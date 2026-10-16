# -*- coding: utf-8 -*-
"""核心应用对象：把配置、数据库、令牌、事件总线、HTTP 服务串起来。

界面层（独立版 / CW 插件版）只依赖这个类，不关心 HTTP 细节。
"""
import threading
import time

from . import auth, config as config_mod, hub as hub_mod, paths
from . import server as server_mod, store as store_mod, util
VERSION = "1.0.1"

LOGIN_WINDOW = 300      # 秒
LOGIN_MAX_FAILS = 8     # 同一 IP 在窗口内的最大失败次数


class SpeakerCore(object):
    def __init__(self, config_path=None, db_path=None):
        self.version = VERSION
        self.config = config_mod.Config(config_path)
        self.store = store_mod.Store(db_path)
        self.tokens = auth.TokenManager()
        self.hub = hub_mod.EventHub()
        self.server = server_mod.SpeakerHTTPServer(self)
        self._login_lock = threading.RLock()
        self._login_fails = {}
        self._stop_event = threading.Event()
        self._housekeeper = None
        self._started_at = None
        self._http_logger = util.Logger(echo=False)

    # ---------------- 生命周期 ----------------
    FALLBACK_SPAN = 300   # 端口不可用时向后尝试的范围

    def _log_environment(self):
        """把运行形态写进日志：排查"资源找不到 / 数据写错地方"最有用的一行。"""
        import sys

        try:
            util.LOG.info(
                "运行形态：frozen={} meipass={} executable={}".format(
                    bool(getattr(sys, "frozen", False)),
                    getattr(sys, "_MEIPASS", "-") or "-",
                    getattr(sys, "executable", "-") or "-",
                )
            )
            util.LOG.info(
                "目录：程序={} 包={} 资源={} 数据={}".format(
                    paths.APP_DIR, paths.PACKAGE_DIR, paths.WEB_DIR, paths.DATA_DIR
                )
            )
        except Exception:
            pass

    def start(self):
        """返回 (ok, message)。

        端口被别的程序占用、或落在 Windows 保留段（Hyper-V/WSL/Docker 会成段保留）
        时会自动顺延到空闲端口，并把新端口写回配置。
        """
        paths.ensure_dirs()
        self._log_environment()
        self._ensure_admin_account()
        ok, message = self.server.start()
        if not ok and self.server.last_error in ("in_use", "denied"):
            ok, message = self._retry_on_free_port(message)
        if ok:
            self._started_at = time.time()
            self._start_housekeeper()
        return ok, message

    def _retry_on_free_port(self, prefix=""):
        wanted = self.config.port
        bind = self.config.bind
        reason = "被系统保留" if self.server.last_error == "denied" else "已被其他程序占用"
        for candidate in range(wanted + 1, wanted + self.FALLBACK_SPAN + 1):
            if not util.port_is_free(candidate, bind):
                continue
            self.config["port"] = candidate
            ok, _message = self.server.start()
            if ok:
                self.config.save()
                util.LOG.warn(
                    "端口 {} {}，已自动改用 {}".format(wanted, reason, candidate)
                )
                return True, "端口 {} {}，已自动改用 {}（教师端地址 {}）".format(
                    wanted, reason, candidate, self.address
                )
            self.config["port"] = wanted
        return False, (
            "端口 {} {}，且 {}~{} 都不可用。请在设置中手动指定一个端口"
            "（可用 netsh int ipv4 show excludedportrange protocol=tcp "
            "查看系统保留段）。".format(
                wanted, reason, wanted + 1, wanted + self.FALLBACK_SPAN
            )
        )

    def stop(self):
        self._stop_event.set()
        self.server.stop()
        try:
            self.store.close()
        except Exception:
            pass

    def _start_housekeeper(self):
        if self._housekeeper is not None:
            return
        thread = threading.Thread(target=self._housekeeping, name="ClassSpeakerHousekeeper")
        thread.daemon = True
        thread.start()
        self._housekeeper = thread

    def _housekeeping(self):
        last_purge = 0.0
        while not self._stop_event.wait(60):
            try:
                self.tokens.purge()
                now = time.time()
                if now - last_purge > 6 * 3600:
                    last_purge = now
                    self.store.purge_old(self.config.get("keep_days", 30))
            except Exception as exc:
                util.LOG.warn("后台清理失败：{}".format(exc))

    # ---------------- 管理员账号 ----------------
    def _ensure_admin_account(self):
        """内置管理员账号 admin：数据库为空时自动创建。"""
        if self.store.get_user_by_name(auth.DEFAULT_ADMIN_NAME):
            return
        salt, digest = auth.hash_password(auth.DEFAULT_ADMIN_PASSWORD)
        try:
            self.store.create_user(
                username=auth.DEFAULT_ADMIN_NAME,
                salt=salt,
                password_hash=digest,
                display_name="管理员",
                role="admin",
                status="approved",
                approved_by="system",
            )
            util.LOG.info(
                "已创建内置管理员账号：{} / {}（请尽快在设置中修改密码）".format(
                    auth.DEFAULT_ADMIN_NAME, auth.DEFAULT_ADMIN_PASSWORD)
            )
        except Exception as exc:
            util.LOG.warn("创建管理员账号失败：{}".format(exc))

    def reset_admin_password(self, new_password):
        ok, message = auth.check_password(new_password)
        if not ok:
            return False, message
        user = self.store.get_user_by_name(auth.DEFAULT_ADMIN_NAME)
        if not user:
            salt, digest = auth.hash_password(new_password)
            self.store.create_user(
                username=auth.DEFAULT_ADMIN_NAME, salt=salt, password_hash=digest,
                display_name="管理员", role="admin", status="approved",
                approved_by="system",
            )
            return True, "已重新创建管理员账号"
        salt, digest = auth.hash_password(new_password)
        self.store.set_user_password(user["id"], salt, digest)
        self.tokens.revoke_user(user["id"])
        util.LOG.info("管理员密码已重置")
        return True, "管理员密码已更新"

    # ---------------- 登录频率限制 ----------------
    def _recent_fails(self, ip):
        now = time.time()
        with self._login_lock:
            fails = [t for t in self._login_fails.get(ip, []) if now - t < LOGIN_WINDOW]
            self._login_fails[ip] = fails
            return fails

    def login_blocked(self, ip):
        return len(self._recent_fails(ip)) >= LOGIN_MAX_FAILS

    def login_failed(self, ip):
        with self._login_lock:
            self._login_fails.setdefault(ip, []).append(time.time())

    def login_succeeded(self, ip):
        with self._login_lock:
            self._login_fails.pop(ip, None)

    # ---------------- 消息 ----------------
    def confirm_message(self, message_id, received_by="classroom"):
        message = self.store.mark_received(message_id, received_by)
        if message:
            util.LOG.info("消息 #{} 已确认收到".format(message_id))
            self.hub.emit({"type": "message_received", "message": message})
        return message

    def inject_test_message(self, content="这是一条测试消息，用于检查弹窗效果。",
                            sender="测试"):
        message = self.store.add_message(0, sender, content)
        self.hub.emit({"type": "message", "message": message})
        return message

    def pending_count(self):
        return self.store.count_pending()

    def pending_messages(self, hours=None):
        """程序重启后需要补弹的未确认消息（默认只看最近 12 小时）。"""
        if hours is None:
            hours = self.config.get("replay_hours", 12)
        return self.store.list_pending(since_hours=hours)

    # ---------------- 信息 ----------------
    @property
    def classroom_name(self):
        return self.config.classroom_name

    @property
    def address(self):
        return "http://{}:{}".format(util.primary_lan_ip(), self.config.port)

    @property
    def addresses(self):
        return ["http://{}:{}".format(ip, self.config.port)
                for ip in util.all_lan_ips()]

    def uptime(self):
        if not self._started_at:
            return 0
        return int(time.time() - self._started_at)

    def http_log(self, message):
        self._http_logger.info(message)

    def apply_port(self, port):
        """修改端口；如果服务在运行则立即重启。"""
        port = int(port)
        if port == self.config.port:
            return True, "端口未变化"
        old_port = self.config.port
        self.config["port"] = port
        self.config.save()
        if self.server.running:
            ok, message = self.server.restart()
            if not ok:
                self.config["port"] = old_port
                self.config.save()
                self.server.restart()
                return False, message
            return True, "端口已更改为 {}".format(port)
        return True, "端口已保存，下次启动生效"

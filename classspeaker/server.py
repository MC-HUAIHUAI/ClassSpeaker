# -*- coding: utf-8 -*-
"""内嵌 HTTP 服务：教师用浏览器访问本机局域网地址即可发消息。

纯标准库实现（http.server），零第三方依赖。
"""
import json
import os
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import auth, paths, util

MAX_BODY = 256 * 1024
MAX_CONTENT_LEN = 1000

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".txt": "text/plain; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

MIME_FALLBACK = "application/octet-stream"


class ApiError(Exception):
    def __init__(self, message, code=400):
        Exception.__init__(self, message)
        self.message = message
        self.code = code


class _Handler(BaseHTTPRequestHandler):
    server_version = "ClassSpeaker"
    sys_version = ""
    timeout = 30

    # ---------- 日志 ----------
    def log_message(self, fmt, *args):
        try:
            self.server.app.http_log("{}{}".format(
                self.address_string(), " " + (fmt % args)))
        except Exception:
            pass

    # ---------- 基础工具 ----------
    def _send_bytes(self, payload, code=200, content_type=MIME_FALLBACK,
                    extra_headers=None):
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            util.LOG.warn("响应写出失败：{}".format(exc))

    def _send_json(self, obj, code=200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send_bytes(payload, code, "application/json; charset=utf-8")

    def _fail(self, message, code=400):
        self._send_json({"ok": False, "error": message}, code)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except Exception:
            length = 0
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ApiError("请求体过大", 413)
        raw = self.rfile.read(length)
        if not raw:
            return {}
        text = raw.decode("utf-8", "replace").strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
        except Exception:
            raise ApiError("请求格式错误（需要 JSON）")
        if not isinstance(data, dict):
            raise ApiError("请求格式错误（需要 JSON 对象）")
        return data

    def _token(self):
        token = self.headers.get("X-Auth-Token") or ""
        if not token:
            authz = self.headers.get("Authorization") or ""
            if authz.lower().startswith("bearer "):
                token = authz[7:].strip()
        return token.strip()

    def _current(self, require_admin=False, require_status=True):
        """返回 (session, user_row)；失败时已写出响应并返回 (None, None)。"""
        app = self.server.app
        token = self._token()
        session = app.tokens.resolve(token)
        if not session:
            self._fail("登录状态已失效，请重新登录", 401)
            return None, None
        user = app.store.get_user(session["user_id"])
        if not user:
            app.tokens.revoke(token)
            self._fail("账号不存在", 401)
            return None, None
        if require_status and user["status"] != "approved":
            app.tokens.revoke(token)
            self._fail("账号尚未通过管理员审批", 403)
            return None, None
        if require_admin and user["role"] != "admin":
            self._fail("需要管理员权限", 403)
            return None, None
        return session, user

    # ---------- 路由 ----------
    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/" or path == "/index.html":
                return self._serve_static("index.html")
            if path.startswith("/static/"):
                return self._serve_static(path[len("/static/"):])
            if path.startswith("/api/"):
                return self._api(method, path)
            return self._fail("接口不存在", 404)
        except ApiError as exc:
            self._fail(exc.message, exc.code)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            util.LOG.exception("处理请求 {} 出错：{}".format(path, exc))
            self._fail("服务器内部错误", 500)

    def _api(self, method, path):
        routes = {
            ("GET", "/api/info"): self._api_info,
            ("GET", "/api/health"): self._api_health,
            ("POST", "/api/register"): self._api_register,
            ("POST", "/api/login"): self._api_login,
            ("POST", "/api/logout"): self._api_logout,
            ("GET", "/api/me"): self._api_me,
            ("POST", "/api/send"): self._api_send,
            ("GET", "/api/messages"): self._api_messages,
            ("GET", "/api/users"): self._api_users,
            ("POST", "/api/users/approve"): self._api_user_approve,
            ("POST", "/api/users/reject"): self._api_user_reject,
            ("POST", "/api/users/delete"): self._api_user_delete,
            ("POST", "/api/password"): self._api_password,
            ("POST", "/api/ack"): self._api_ack,
        }
        handler = routes.get((method, path))
        if handler is None:
            if method == "GET":
                raise ApiError("接口不存在", 404)
            raise ApiError("接口不存在", 404)
        return handler()

    # ---------- 静态资源 ----------
    def _serve_static(self, relative):
        relative = relative.split("?", 1)[0].lstrip("/\\")
        base = os.path.normpath(paths.WEB_DIR)
        target = os.path.normpath(os.path.join(base, relative.replace("/", os.sep)))
        if not target.startswith(base) or not os.path.isfile(target):
            return self._fail("资源不存在", 404)
        ext = os.path.splitext(target)[1].lower()
        try:
            with open(target, "rb") as fh:
                payload = fh.read()
        except Exception as exc:
            util.LOG.warn("读取静态资源失败：{}".format(exc))
            return self._fail("资源读取失败", 500)
        self._send_bytes(payload, 200, CONTENT_TYPES.get(ext, MIME_FALLBACK))

    # ---------- 公开接口 ----------
    def _api_health(self):
        app = self.server.app
        self._send_json({
            "ok": True,
            "app": "ClassSpeaker",
            "version": app.version,
            "time": util.now_str(),
            "pending": app.store.count_pending(),
        })

    def _api_info(self):
        app = self.server.app
        self._send_json({
            "ok": True,
            "classroom": app.classroom_name,
            "hostname": util.hostname(),
            "ips": util.all_lan_ips(),
            "address": app.address,
            "port": app.config.port,
            "require_approval": bool(app.config.get("require_approval", True)),
            "admin_exists": app.store.count_users("approved") > 0,
            "pending_users": app.store.count_users("pending"),
            "version": app.version,
            "server_time": util.now_str(),
        })

    # ---------- 账号 ----------
    def _api_register(self):
        app = self.server.app
        data = self._body()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        display_name = (data.get("display_name") or "").strip()[:32]

        ok, message = auth.check_username(username)
        if not ok:
            raise ApiError(message)
        ok, message = auth.check_password(password)
        if not ok:
            raise ApiError(message)
        if app.store.get_user_by_name(username):
            raise ApiError("用户名已被占用")

        require_approval = bool(app.config.get("require_approval", True))
        is_first = app.store.count_users() == 0
        status = "approved" if (is_first or not require_approval) else "pending"
        salt, digest = auth.hash_password(password)
        try:
            user_id = app.store.create_user(
                username=username,
                salt=salt,
                password_hash=digest,
                display_name=display_name or username,
                role="admin" if is_first else "teacher",
                status=status,
                approved_by="system" if is_first else "",
            )
        except Exception:
            raise ApiError("用户名已被占用")

        app.hub.emit({"type": "users_changed"})
        util.LOG.info("新账号注册：{}（{}）".format(username, status))
        self._send_json({
            "ok": True,
            "status": status,
            "user_id": user_id,
            "message": "注册成功，请登录" if status == "approved"
                       else "注册成功，等待管理员审批后即可登录",
        })

    def _api_login(self):
        app = self.server.app
        ip = self.client_address[0]
        if app.login_blocked(ip):
            raise ApiError("尝试次数过多，请稍后再试", 429)
        data = self._body()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        user = app.store.get_user_by_name(username)
        if not user or not auth.verify_password(password, user["salt"],
                                                 user["password_hash"]):
            app.login_failed(ip)
            raise ApiError("用户名或密码错误", 401)
        if user["status"] == "pending":
            raise ApiError("账号正在等待管理员审批，请联系管理员", 403)
        if user["status"] == "rejected":
            raise ApiError("账号申请已被拒绝，请联系管理员", 403)
        app.login_succeeded(ip)
        app.store.touch_login(user["id"])
        token = app.tokens.issue(user)
        util.LOG.info("教师登录：{}（{}）".format(user["username"], ip))
        self._send_json({
            "ok": True,
            "token": token,
            "user": self._user_public(user),
            "classroom": app.classroom_name,
        })

    def _api_logout(self):
        app = self.server.app
        token = self._token()
        app.tokens.revoke(token)
        self._send_json({"ok": True})

    def _api_me(self):
        session, user = self._current()
        if not user:
            return
        app = self.server.app
        self._send_json({
            "ok": True,
            "user": self._user_public(user),
            "classroom": app.classroom_name,
            "address": app.address,
            "pending_users": app.store.count_users("pending"),
        })

    @staticmethod
    def _user_public(user):
        return {
            "id": user["id"],
            "username": user["username"],
            "display_name": user.get("display_name") or user["username"],
            "role": user.get("role", "teacher"),
            "status": user.get("status", "approved"),
            "created_at": user.get("created_at", ""),
            "last_login": user.get("last_login", ""),
        }

    def _api_password(self):
        session, user = self._current()
        if not user:
            return
        app = self.server.app
        data = self._body()
        old = data.get("old_password") or ""
        new = data.get("new_password") or ""
        if not auth.verify_password(old, user["salt"], user["password_hash"]):
            raise ApiError("原密码不正确")
        ok, message = auth.check_password(new)
        if not ok:
            raise ApiError(message)
        salt, digest = auth.hash_password(new)
        app.store.set_user_password(user["id"], salt, digest)
        app.tokens.revoke_user(user["id"])
        self._send_json({"ok": True, "message": "密码已修改，请重新登录"})

    # ---------- 消息 ----------
    def _api_send(self):
        session, user = self._current()
        if not user:
            return
        app = self.server.app
        data = self._body()
        content = (data.get("content") or "").strip()
        if not content:
            raise ApiError("消息内容不能为空")
        if len(content) > MAX_CONTENT_LEN:
            raise ApiError("消息内容过长（最多 {} 字）".format(MAX_CONTENT_LEN))
        sender_name = (user.get("display_name") or "").strip() or user["username"]
        message = app.store.add_message(user["id"], sender_name, content)
        util.LOG.info("{} 发送消息 #{}".format(sender_name, message["id"]))
        app.hub.emit({"type": "message", "message": message})
        self._send_json({"ok": True, "message": self._message_public(message)})

    @staticmethod
    def _message_public(message):
        return {
            "id": message["id"],
            "sender_name": message.get("sender_name", ""),
            "content": message.get("content", ""),
            "created_at": message.get("created_at", ""),
            "status": message.get("status", "pending"),
            "received_at": message.get("received_at", ""),
        }

    def _api_messages(self):
        session, user = self._current()
        if not user:
            return
        app = self.server.app
        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        limit = 100
        for part in query.split("&"):
            if part.startswith("limit="):
                try:
                    limit = int(part[6:])
                except Exception:
                    limit = 100
        sender_id = None if user["role"] == "admin" else user["id"]
        rows = app.store.list_messages(sender_id=sender_id, limit=limit)
        self._send_json({
            "ok": True,
            "messages": [self._message_public(row) for row in rows],
            "pending": app.store.count_pending(sender_id),
        })

    def _api_ack(self):
        """供教室端（或调试工具）确认收到。"""
        session, user = self._current()
        if not user:
            return
        app = self.server.app
        data = self._body()
        try:
            message_id = int(data.get("message_id") or 0)
        except Exception:
            message_id = 0
        if message_id <= 0:
            raise ApiError("缺少 message_id")
        app.confirm_message(message_id, received_by="web:" + user["username"])
        self._send_json({"ok": True})

    # ---------- 管理员 ----------
    def _api_users(self):
        session, user = self._current(require_admin=True)
        if not user:
            return
        app = self.server.app
        rows = app.store.list_users()
        users = []
        for row in rows:
            item = self._user_public(row)
            item["approved_at"] = row.get("approved_at", "")
            item["approved_by"] = row.get("approved_by", "")
            users.append(item)
        self._send_json({"ok": True, "users": users})

    def _api_user_approve(self):
        self._user_action("approve")

    def _api_user_reject(self):
        self._user_action("reject")

    def _api_user_delete(self):
        self._user_action("delete")

    def _user_action(self, action):
        session, admin = self._current(require_admin=True)
        if not admin:
            return
        app = self.server.app
        data = self._body()
        try:
            user_id = int(data.get("user_id") or 0)
        except Exception:
            user_id = 0
        if user_id <= 0:
            raise ApiError("缺少 user_id")
        target = app.store.get_user(user_id)
        if not target:
            raise ApiError("账号不存在", 404)

        if action == "approve":
            if target["status"] == "approved":
                raise ApiError("该账号已是启用状态")
            app.store.set_user_status(user_id, "approved", approved_by=admin["username"])
            app.tokens.revoke_user(user_id)
            util.LOG.info("管理员 {} 批准账号 {}".format(admin["username"],
                                                        target["username"]))
            message = "已批准该账号"
        elif action == "reject":
            if target["role"] == "admin":
                raise ApiError("不能拒绝管理员账号")
            app.store.set_user_status(user_id, "rejected", approved_by=admin["username"])
            app.tokens.revoke_user(user_id)
            util.LOG.info("管理员 {} 拒绝账号 {}".format(admin["username"],
                                                        target["username"]))
            message = "已拒绝该账号"
        else:
            if target["id"] == admin["id"]:
                raise ApiError("不能删除自己的账号")
            if target["role"] == "admin" and app.store.count_users("approved") <= 1:
                raise ApiError("至少需要保留一个管理员账号")
            app.store.delete_user(user_id)
            app.tokens.revoke_user(user_id)
            util.LOG.info("管理员 {} 删除账号 {}".format(admin["username"],
                                                        target["username"]))
            message = "已删除该账号"

        app.hub.emit({"type": "users_changed"})
        self._send_json({"ok": True, "message": message})


class _HTTPServer(ThreadingHTTPServer):
    """坚决不允许抢绑端口。

    http.server.HTTPServer 默认 allow_reuse_address = 1，在 Windows 上会让
    两个进程同时监听同一端口（例如 Docker 的 com.docker.backend 常驻 8080），
    连接被随机投递给另一方，教师端就会 ERR_CONNECTION_REFUSED。
    关掉它，端口被占用时 bind 会直接失败，我们才能明确报错并自动换端口。
    """

    daemon_threads = True
    allow_reuse_address = False
    allow_reuse_port = False


class SpeakerHTTPServer(object):
    """对外的服务封装：启动 / 停止 / 状态。"""

    def __init__(self, app):
        self.app = app
        self._httpd = None
        self._thread = None
        self._lock = threading.RLock()
        self.last_error = ""

    @property
    def running(self):
        return self._httpd is not None

    def start(self):
        with self._lock:
            if self._httpd is not None:
                return True, "服务已在运行"
            self.last_error = ""
            bind = self.app.config.bind
            port = self.app.config.port
            try:
                httpd = _HTTPServer((bind, port), _Handler)
            except OSError as exc:
                errno_value = getattr(exc, "errno", None)
                if errno_value in (48, 98, 10048):
                    self.last_error = "in_use"
                    return False, "端口 {} 已被其他程序占用".format(port)
                if errno_value in (13, 10013):
                    self.last_error = "denied"
                    return False, "端口 {} 被系统保留或无权限绑定".format(port)
                self.last_error = "other"
                return False, "无法绑定 {}:{} - {}".format(bind, port, exc)
            httpd.app = self.app
            self._httpd = httpd
            self._thread = threading.Thread(
                target=httpd.serve_forever, kwargs={"poll_interval": 0.3},
                name="ClassSpeakerHTTP",
            )
            self._thread.daemon = True
            self._thread.start()
            util.LOG.info("HTTP 服务已启动：{}".format(self.app.address))
            return True, "服务已启动"

    def stop(self):
        with self._lock:
            if self._httpd is None:
                return
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            try:
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
            self._thread = None
            util.LOG.info("HTTP 服务已停止")

    def restart(self):
        self.stop()
        time.sleep(0.2)
        return self.start()

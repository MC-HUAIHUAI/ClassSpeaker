# -*- coding: utf-8 -*-
"""端到端冒烟测试（不需要 PyQt5）。

    python tools/smoke_test.py

覆盖：内置 admin 账号 -> 教师注册（待审批）-> 管理员审批 -> 登录 ->
发送消息 -> 教室端"确认收到" -> 教师端看到回执。
"""
import json
import os
import shutil
import socket
import sys
import tempfile
import urllib.error
import urllib.request

# 让中文输出在任意控制台代码页下都不会崩（CI 上是英文环境）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 让测试用临时数据目录，绝不动正式配置与数据库
os.environ["CLASSSPEAKER_DATA_DIR"] = tempfile.mkdtemp(prefix="classspeaker_smoke_data_")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from classspeaker import SpeakerCore, auth, util  # noqa: E402

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  [PASS] {}{}".format(name, ("  " + detail) if detail else ""))
    else:
        FAILED.append(name)
        print("  [FAIL] {}{}".format(name, ("  " + detail) if detail else ""))


def request(port, path, method="GET", body=None, token=None):
    url = "http://127.0.0.1:{}{}".format(port, path)
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Auth-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw}


def main():
    temp_dir = tempfile.mkdtemp(prefix="classspeaker_test_")
    events = []
    port = util.find_free_port(18080, 18160) or 18080
    core = None
    try:
        core = SpeakerCore(
            config_path=os.path.join(temp_dir, "config.json"),
            db_path=os.path.join(temp_dir, "speaker.db"),
        )
        core.config["port"] = port
        core.config.save()
        core.hub.subscribe(lambda event: events.append(event))

        print("\n== 启动服务 ==")
        ok, message = core.start()
        check("服务启动", ok, message)

        print("\n== 公开接口 ==")
        status, info = request(port, "/api/info")
        check("GET /api/info", status == 200 and info.get("ok"),
              "classroom={}".format(info.get("classroom")))
        status, health = request(port, "/api/health")
        check("GET /api/health", status == 200 and health.get("ok"))

        print("\n== 管理员账号 ==")
        status, data = request(port, "/api/login", "POST",
                               {"username": "admin", "password": "admin123"})
        check("内置 admin 可登录", status == 200 and data.get("token"), str(data))
        admin_token = data.get("token", "")
        check("管理员角色正确",
              data.get("user", {}).get("role") == "admin")

        status, data = request(port, "/api/login", "POST",
                               {"username": "admin", "password": "wrong"})
        check("错误密码被拒绝", status == 401)

        print("\n== 教师注册与审批 ==")
        status, data = request(port, "/api/register", "POST", {
            "username": "teacher01", "password": "pass1234",
            "display_name": "张老师",
        })
        check("注册成功", status == 200 and data.get("status") == "pending", str(data))

        status, data = request(port, "/api/login", "POST",
                               {"username": "teacher01", "password": "pass1234"})
        check("未审批不能登录", status == 403)

        status, data = request(port, "/api/users", token=admin_token)
        users = data.get("users", [])
        check("管理员可列出账号", status == 200 and len(users) >= 2)
        target = [u for u in users if u["username"] == "teacher01"]
        check("账号出现在列表中", bool(target))
        teacher_id = target[0]["id"] if target else 0

        status, data = request(port, "/api/users/approve", "POST",
                               {"user_id": teacher_id}, admin_token)
        check("审批通过", status == 200 and data.get("ok"), str(data))

        status, data = request(port, "/api/login", "POST",
                               {"username": "teacher01", "password": "pass1234"})
        check("审批后可登录", status == 200 and data.get("token"))
        teacher_token = data.get("token", "")
        check("姓名回显为张老师",
              data.get("user", {}).get("display_name") == "张老师")

        print("\n== 发送消息 ==")
        status, data = request(port, "/api/send", "POST",
                               {"content": "请第三排同学上讲台领取试卷。"}, teacher_token)
        check("发送成功", status == 200 and data.get("message", {}).get("id"),
              str(data))
        message_id = data.get("message", {}).get("id")

        status, data = request(port, "/api/send", "POST", {"content": "   "},
                               teacher_token)
        check("空消息被拒绝", status == 400)

        check("弹窗事件已派发",
              any(e.get("type") == "message" for e in events))

        status, data = request(port, "/api/messages", token=teacher_token)
        msgs = data.get("messages", [])
        check("教师能看到自己的消息", status == 200 and len(msgs) == 1)
        check("初始状态为待确认",
              msgs and msgs[0]["status"] == "pending")

        status, data = request(port, "/api/messages", token=admin_token)
        check("管理员能看到全部消息", status == 200 and len(data.get("messages", [])) == 1)

        print("\n== 教室端确认收到 ==")
        core.confirm_message(message_id, received_by="测试教室")
        status, data = request(port, "/api/messages", token=teacher_token)
        msgs = data.get("messages", [])
        check("状态变为已确认",
              msgs and msgs[0]["status"] == "received")
        check("带确认时间", bool(msgs and msgs[0]["received_at"]))
        check("回执事件已派发",
              any(e.get("type") == "message_received" for e in events))

        print("\n== 未确认消息查询（重启补弹用）==")
        core.inject_test_message("补弹测试消息", "李老师")
        pending = core.pending_messages()
        check("能查到未确认消息",
              len(pending) == 1 and pending[0]["content"] == "补弹测试消息",
              "count={}".format(len(pending)))
        core.store._exec(
            "UPDATE messages SET created_at = datetime('now','localtime','-20 hours')"
        )
        check("超出补弹时间窗口的不再补弹", core.pending_messages(hours=12) == [])
        core.store._exec(
            "UPDATE messages SET created_at = datetime('now','localtime')"
        )
        core.confirm_message(pending[0]["id"], "测试教室")

        print("\n== 权限与账号安全 ==")
        status, data = request(port, "/api/users", token=teacher_token)
        check("普通教师无权看账号列表", status == 403)
        status, data = request(port, "/api/send", "POST", {"content": "x"})
        check("无令牌不能发送", status == 401)

        status, data = request(port, "/api/users/delete", "POST",
                               {"user_id": 1}, admin_token)
        check("不能删除自己", status == 400, str(data))

        status, data = request(port, "/api/password", "POST", {
            "old_password": "pass1234", "new_password": "newpass123",
        }, teacher_token)
        check("教师可改密码", status == 200, str(data))
        status, data = request(port, "/api/login", "POST",
                               {"username": "teacher01", "password": "newpass123"})
        check("新密码可登录", status == 200)

        hash_ok = auth.verify_password("admin123",
                                       core.store.get_user_by_name("admin")["salt"],
                                       core.store.get_user_by_name("admin")["password_hash"])
        check("密码以哈希方式存储", hash_ok)

        print("\n== 端口冲突处理 ==")
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("0.0.0.0", 0))
        blocked_port = blocker.getsockname()[1]
        blocker.listen(1)
        core2 = None
        try:
            check("探测函数能识别被占用端口",
                  util.port_is_free(blocked_port) is False)
            core2 = SpeakerCore(
                config_path=os.path.join(temp_dir, "config2.json"),
                db_path=os.path.join(temp_dir, "speaker2.db"),
            )
            core2.config["port"] = blocked_port
            ok2, msg2 = core2.start()
            check("端口被占用时自动换端口",
                  ok2 and core2.config.port != blocked_port, msg2)
            status2, health2 = request(core2.config.port, "/api/health")
            check("换端口后服务可正常访问",
                  status2 == 200 and health2.get("ok"),
                  "port={}".format(core2.config.port))
        finally:
            if core2 is not None:
                core2.stop()
            blocker.close()

        print("\n== 路径解析（三种运行形态，防回归）==")
        from classspeaker import paths as cs_paths

        check("源码运行 → 用包的父目录",
              cs_paths.resolve_app_dir(r"F:\proj\classspeaker", "", r"C:\Python\python.exe")
              == r"F:\proj")
        check("CW 插件 → 用插件目录，而非宿主的 _MEIPASS",
              cs_paths.resolve_app_dir(
                  r"C:\CW\plugins\ClassSpeaker\classspeaker",
                  r"C:\CW",                       # onedir 打包的宿主：_MEIPASS 就是安装目录
                  r"C:\CW\ClassWidgets.exe",
                  r"C:\Users\x\AppData\Local\Temp")
              == r"C:\CW\plugins\ClassSpeaker",
              "（CW 自己是 onedir 打包，sys.frozen/_MEIPASS 在它进程里都成立）")
        check("打包 exe(onefile) → 用 exe 所在目录，不落在临时目录",
              cs_paths.resolve_app_dir(
                  r"C:\Users\x\AppData\Local\Temp\_MEI1\classspeaker",
                  r"C:\Users\x\AppData\Local\Temp\_MEI1",
                  r"D:\App\ClassSpeaker.exe",
                  r"C:\Users\x\AppData\Local\Temp")
              == r"D:\App")
        check("打包 exe(onedir) → 同样用 exe 所在目录",
              cs_paths.resolve_app_dir(
                  r"D:\App\classspeaker", r"D:\App", r"D:\App\ClassSpeaker.exe",
                  r"C:\Users\x\AppData\Local\Temp")
              == r"D:\App")
        check("资源目录就在本包旁边",
              cs_paths.WEB_DIR.endswith(os.path.join("classspeaker", "web"))
              and os.path.isfile(os.path.join(cs_paths.WEB_DIR, "index.html")),
              cs_paths.WEB_DIR)
        check("内置声音文件存在",
              os.path.isfile(cs_paths.DEFAULT_SOUND), cs_paths.DEFAULT_SOUND)

        print("\n== 静态资源 ==")
        status, _ = request(port, "/")
        check("首页可访问", status == 200)
        status, data = request(port, "/static/app.js")
        check("前端脚本可访问", status == 200 and "raw" in data)
        status, _ = request(port, "/static/%2e%2e/core/app.py")
        check("目录穿越被拦截", status == 404)
    finally:
        if core is not None:
            core.stop()
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n================ 结果 ================")
    print("通过 {} 项，失败 {} 项".format(len(PASSED), len(FAILED)))
    if FAILED:
        for name in FAILED:
            print(" - 失败：{}".format(name))
        return 1
    print("全部通过 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())

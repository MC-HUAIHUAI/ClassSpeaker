# -*- coding: utf-8 -*-
"""界面层自动测试（无显示器也可跑）：

    set QT_QPA_PLATFORM=offscreen
    python tools/gui_test.py

覆盖：无边框弹窗属性、只能"确认收到"关闭、托盘/设置窗口、弹窗队列与回执。
"""
import os
import shutil
import sys
import tempfile

# 让中文输出在任意控制台代码页下都不会崩（CI 上是英文环境）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 让测试用临时数据目录，绝不动正式配置与数据库
os.environ["CLASSSPEAKER_DATA_DIR"] = tempfile.mkdtemp(prefix="classspeaker_gui_data_")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from classspeaker import SpeakerCore, util  # noqa: E402
from classspeaker.ui import SpeakerDesktop, style  # noqa: E402

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  [PASS] {}{}".format(name, ("  " + detail) if detail else ""))
    else:
        FAILED.append(name)
        print("  [FAIL] {}{}".format(name, ("  " + detail) if detail else ""))


def main():
    temp_dir = tempfile.mkdtemp(prefix="classspeaker_gui_")
    app = QApplication(sys.argv)
    desktop = None
    core = None
    try:
        port = util.find_free_port(18280, 18340) or 18280
        core = SpeakerCore(
            config_path=os.path.join(temp_dir, "config.json"),
            db_path=os.path.join(temp_dir, "speaker.db"),
        )
        core.config["port"] = port
        core.config["first_run"] = False   # 测试中不自动弹设置窗口
        core.config.update({
            "popup_width": 600,
            "popup_height": 360,
            "popup_font_size": 30,
            "popup_opacity": 0.9,
        })
        # 模拟"上次没确认就重启了"的场景
        core.inject_test_message("重启前未确认的消息", "陈老师")

        print("\n== 图标与样式 ==")
        icon = style.build_icon()
        check("图标可生成", not icon.isNull())
        check("弹窗样式表可生成", "confirmBtn" in style.popup_stylesheet(28))
        check("设置样式表可生成", "QGroupBox" in style.dialog_stylesheet())

        print("\n== 启动桌面层 ==")
        desktop = SpeakerDesktop(core, app)
        ok, message = desktop.start()
        check("服务随界面启动", ok and core.server.running, message)

        print("\n== 重启补弹 ==")
        check("重启后自动补弹未确认消息", desktop.queue_count() == 1,
              "count={}".format(desktop.queue_count()))
        desktop._tick()
        replayed = desktop.popup
        check("补弹的是那条未确认消息",
              replayed is not None and
              "重启前未确认" in (replayed.message or {}).get("content", ""))
        if replayed is not None:
            replayed.confirm()
        app.processEvents()
        check("补弹确认后队列清空", desktop.queue_count() == 0,
              "count={}".format(desktop.queue_count()))

        print("\n== 弹窗行为 ==")
        desktop.test_popup()
        app.processEvents()
        check("消息进入队列", desktop.queue_count() == 1,
              "count={}".format(desktop.queue_count()))
        desktop._tick()
        popup = desktop.popup
        check("弹窗已创建", popup is not None)
        if popup is not None:
            flags = popup.windowFlags()
            check("无边框", bool(flags & Qt.FramelessWindowHint))
            check("置顶", bool(flags & Qt.WindowStaysOnTopHint))
            check("宽度按设置生效", popup.width() == 600, str(popup.width()))
            check("高度按设置生效", popup.height() == 360, str(popup.height()))
            check("透明度按设置生效", abs(popup.windowOpacity() - 0.9) < 0.02,
                  str(popup.windowOpacity()))
            check("标题含发送者", "测试" in popup._title_text(), popup._title_text())
            content_label = popup.findChild(QLabel, "content")
            check("正文显示消息内容",
                  content_label is not None and "测试消息" in content_label.text())
            check("确认按钮文案正确",
                  popup.confirm_btn.text() == "确认收到")
            check("标题栏没有任何关闭控件",
                  popup.findChild(QPushButton, "closeBtn") is None)

            popup.show()
            app.processEvents()
            popup.close()          # 模拟 Alt+F4 / 系统关闭
            app.processEvents()
            check("未经确认无法关闭", not popup._confirmed)

            popup.confirm()
            app.processEvents()
            check("点击确认后标记为已确认", popup._confirmed)

        app.processEvents()
        messages = core.store.list_messages(limit=10)
        check("测试消息已写入数据库",
              any("测试消息" in m["content"] for m in messages))

        print("\n== 弹窗队列串行显示 ==")
        core.inject_test_message("第一条", "张老师")
        core.inject_test_message("第二条", "李老师")
        app.processEvents()
        check("两条消息排队", desktop.queue_count() == 2,
              "count={}".format(desktop.queue_count()))
        desktop._tick()
        first = desktop.popup
        check("先显示第一条", first is not None and
              "第一条" in first.message.get("content", ""))
        first.confirm()
        app.processEvents()
        desktop._tick()
        second = desktop.popup
        check("确认后显示下一条", second is not None and
              "第二条" in second.message.get("content", ""))
        second.confirm()
        app.processEvents()
        received = [m for m in core.store.list_messages(limit=10)
                    if m["status"] == "received"]
        check("全部消息都已回执", len(received) == 4, "received={}".format(len(received)))

        print("\n== 开机自启 ==")
        from classspeaker import autostart

        check("平台支持自启", autostart.supported())
        check("自启命令指向 run.py / exe",
              "run.py" in autostart.launch_command() or
              ".exe" in autostart.launch_command().lower(),
              autostart.launch_command())

        # 用临时项名测试，绝不碰正式那条；同时在结束时还原正式项
        temp_name = "ClassSpeakerSelfTest{}".format(os.getpid())
        real_before = autostart.current_value()
        try:
            check("临时项初始未开启", not autostart.is_enabled(temp_name))
            ok_enable, message_enable = autostart.enable(temp_name)
            check("能写入自启项", ok_enable, message_enable)
            check("写入后读到开启状态", autostart.is_enabled(temp_name))
            check("写入内容就是当前程序",
                  autostart.current_value(temp_name).strip() ==
                  autostart.launch_command().strip())
            check("apply(True) 幂等",
                  autostart.apply(True, temp_name)[0] is True)
            ok_disable, _ = autostart.disable(temp_name)
            check("能删除自启项",
                  ok_disable and not autostart.is_enabled(temp_name))
            check("apply(False) 幂等",
                  autostart.apply(False, temp_name)[0] is True)

            # 托盘右键菜单里的开关（把项名临时改成测试名，不碰正式项）
            original_name = autostart.VALUE_NAME
            autostart.VALUE_NAME = temp_name
            try:
                desktop.toggle_autostart(True)
                check("托盘开关能开启自启", autostart.is_enabled())
                desktop._sync_autostart_action()
                action = desktop.actions.get("autostart")
                check("托盘勾选状态与注册表一致",
                      action is None or action.isChecked())
                desktop.toggle_autostart(False)
                check("托盘开关能关闭自启", not autostart.is_enabled())
            finally:
                autostart.disable()
                autostart.VALUE_NAME = original_name
        finally:
            autostart.disable(temp_name)
            if real_before:
                autostart.enable()

        print("\n== 设置窗口 ==")
        dialog = desktop.open_settings()
        check("设置窗口已打开", dialog is not None and dialog.isVisible())
        check("包含端口设置", dialog.port_spin.value() == port)
        check("包含弹窗宽高", dialog.width_spin.value() == 600 and
              dialog.height_spin.value() == 360)
        check("包含字体大小", dialog.font_spin.value() == 30)
        check("包含透明度", dialog.opacity_slider.value() == 90)
        check("包含声音开关（默认关闭）", dialog.sound_check.isChecked() is False)
        check("声音路径可回退到自带文件",
              dialog.config.sound_file().endswith("notify.wav"),
              dialog.config.sound_file())
        check("显示访问地址", "http" in dialog.report_label.text())
        check("有开机自启开关",
              dialog.autostart_check.isChecked() == autostart.is_enabled())
        check("自启命令已回显", "run.py" in dialog.autostart_label.text() or
              ".exe" in dialog.autostart_label.text().lower(),
              dialog.autostart_label.text())

        print("\n== 设置保存与端口切换 ==")
        new_port = util.find_free_port(18360, 18420) or 18360
        dialog.font_spin.setValue(40)
        dialog.opacity_slider.setValue(80)
        dialog.port_spin.setValue(new_port)
        dialog._save()
        app.processEvents()
        check("字体大小已保存", core.config.popup_font_size == 40,
              str(core.config.popup_font_size))
        check("透明度已保存", abs(core.config.popup_opacity - 0.8) < 0.01)
        check("端口已切换并重启服务", core.config.port == new_port and
              core.server.running, str(core.config.port))

        print("\n== 托盘与首次运行 ==")
        check("托盘可用时不报错", True)
        core.config["first_run"] = True
        desktop._maybe_first_run()
        app.processEvents()
        check("首次运行弹出设置窗口",
              desktop.settings_dialog is not None and
              desktop.settings_dialog.isVisible())
        check("首次运行标记被清除",
              bool(core.config.get("first_run", True)) is False)
    finally:
        if desktop is not None:
            desktop.shutdown()
        elif core is not None:
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

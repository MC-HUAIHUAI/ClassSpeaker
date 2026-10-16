# -*- coding: utf-8 -*-
"""桌面层：托盘图标、设置窗口、弹窗队列。

独立版和 Class Widgets 插件版共用这一层，
区别只在于谁先创建 QApplication。
"""
from collections import deque

from PyQt5.QtCore import QObject, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QMessageBox as QtMessageBox,
    QSystemTrayIcon,
)

from .. import autostart, util

from . import style
from .popup import MessageBox
from .settings import SettingsDialog


class SpeakerDesktop(QObject):
    TICK_MS = 250

    def __init__(self, core, app=None, use_tray=True):
        super(SpeakerDesktop, self).__init__(None)
        self.core = core
        self.app = app or QApplication.instance()
        self.use_tray = bool(use_tray)
        self.queue = deque()
        self.popup = None
        self.settings_dialog = None
        self.tray = None
        self.menu = None
        self.actions = {}
        self.started = False
        self._syncing_autostart = False

        self.timer = QTimer(self)
        self.timer.setInterval(self.TICK_MS)
        self.timer.timeout.connect(self._tick)

    # ---------------- 启动 / 停止 ----------------
    def start(self):
        if self.started:
            return True, "已在运行"
        self.core.hub.subscribe(self._on_event)

        ok, message = self.core.start()
        self._build_tray()
        self._replay_pending()
        self.timer.start()

        if not ok:
            util.LOG.error("服务启动失败：{}".format(message))
            self._notify("服务启动失败", message, warning=True)
            self._show_fatal(message)
        elif self.core.config.get("show_notification_on_start", True):
            self._notify(
                "{} 已启动".format(style.APP_TITLE),
                "教师端地址：{}\n把该地址发给老师即可发送消息。".format(self.core.address),
            )

        self._refresh_tray()
        self.started = True
        QTimer.singleShot(400, self._maybe_first_run)
        return ok, message

    def shutdown(self):
        try:
            self.timer.stop()
        except Exception:
            pass
        if self.popup is not None:
            try:
                self.popup.stop_sound()
                self.popup._confirmed = True
                self.popup.close()
            except Exception:
                pass
            self.popup = None
        if self.tray is not None:
            try:
                self.tray.hide()
            except Exception:
                pass
        try:
            self.core.hub.unsubscribe(self._on_event)
        except Exception:
            pass
        try:
            self.core.stop()
        except Exception:
            pass

    # ---------------- 托盘 ----------------
    def _build_tray(self):
        if not self.use_tray:
            util.LOG.info("按配置跳过托盘图标（设置可在 Class Widgets 插件设置页里改）")
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            util.LOG.warn("系统托盘不可用，设置窗口只能通过首次运行或外部调用打开")
            return
        self.tray = QSystemTrayIcon(style.build_icon(), self)
        self.tray.setToolTip(style.APP_TITLE)

        menu = QMenu()
        info = QAction(self.core.classroom_name, menu)
        info.setEnabled(False)
        menu.addAction(info)
        address = QAction(self.core.address, menu)
        address.setEnabled(False)
        menu.addAction(address)
        self.actions["info"] = info
        self.actions["address"] = address
        menu.addSeparator()

        self._add_action(menu, "settings", "设置…", self.open_settings)
        self._add_action(menu, "test", "测试弹窗", self.test_popup)
        self._add_action(menu, "copy", "复制访问地址", self.copy_address)
        self._add_action(menu, "browse", "在浏览器中打开教师端", self.open_web)

        autostart_action = QAction("开机自动启动", menu)
        autostart_action.setCheckable(True)
        autostart_action.setChecked(autostart.is_enabled())
        autostart_action.toggled.connect(self.toggle_autostart)
        menu.addAction(autostart_action)
        self.actions["autostart"] = autostart_action

        self._add_action(menu, "author", style.AUTHOR_BUTTON_TEXT, self.open_author)
        menu.addSeparator()
        self._add_action(menu, "quit", "退出", self.quit)

        self.menu = menu
        menu.aboutToShow.connect(self._sync_autostart_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _add_action(self, menu, key, text, slot):
        action = QAction(text, menu)
        action.triggered.connect(slot)
        menu.addAction(action)
        self.actions[key] = action
        return action

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.open_settings()

    def _refresh_tray(self):
        if self.tray is None:
            return
        pending = self.queue_count() + self.core.pending_count()
        status = "运行中" if self.core.server.running else "未运行"
        self.tray.setToolTip(
            "{}\n教室：{}\n状态：{}　待确认：{} 条\n{}".format(
                style.APP_TITLE, self.core.classroom_name, status,
                pending, self.core.address,
            )
        )
        if "info" in self.actions:
            self.actions["info"].setText(
                "教室：{}".format(self.core.classroom_name)
            )
        if "address" in self.actions:
            self.actions["address"].setText(self.core.address)

    def queue_count(self):
        return len(self.queue) + (1 if self.popup is not None else 0)

    def _notify(self, title, message, warning=False):
        if self.tray is None:
            return
        icon = QSystemTrayIcon.Warning if warning else QSystemTrayIcon.Information
        try:
            self.tray.showMessage(title, message, icon, 8000)
        except Exception:
            pass

    # ---------------- 事件 ----------------
    def _replay_pending(self):
        """补弹：上次运行期间没被确认的消息，重启后重新弹出来。"""
        if not self.core.config.get("replay_pending_on_start", True):
            return
        try:
            messages = self.core.pending_messages()
        except Exception as exc:
            util.LOG.warn("读取未确认消息失败：{}".format(exc))
            return
        for message in messages:
            self.queue.append(message)
        if messages:
            util.LOG.info("补弹 {} 条未确认消息".format(len(messages)))
            self._refresh_tray()

    def _on_event(self, event):
        kind = (event or {}).get("type")
        if kind == "message":
            message = event.get("message") or {}
            self.queue.append(message)
            self._refresh_tray()
        elif kind == "users_changed":
            self._refresh_tray()

    def _tick(self):
        if self.popup is not None:
            return
        if not self.queue:
            return
        message = self.queue.popleft()
        self._show_popup(message)

    def _show_popup(self, message):
        try:
            popup = MessageBox(self.core.config, message, None)
        except Exception as exc:
            util.LOG.exception("弹窗创建失败：{}".format(exc))
            return
        popup.confirmed.connect(self._on_confirmed)
        self.popup = popup
        popup.show()
        self._refresh_tray()

    def _on_confirmed(self, message_id):
        sender_name = ""
        if self.popup is not None:
            sender_name = (self.popup.message or {}).get("sender_name") or ""
        self.popup = None
        if message_id:
            try:
                self.core.confirm_message(
                    message_id,
                    received_by="{}（{}）".format(self.core.classroom_name,
                                                 util.hostname()),
                )
            except Exception as exc:
                util.LOG.warn("确认消息失败：{}".format(exc))
        _ = sender_name
        self._refresh_tray()
        # 稍等一下再显示下一条，避免弹窗闪断
        QTimer.singleShot(300, self._tick)

    # ---------------- 菜单动作 ----------------
    def open_settings(self):
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return self.settings_dialog
        dialog = SettingsDialog(self.core, None)
        dialog.saved.connect(lambda _values: self._refresh_tray())
        self.settings_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def _maybe_first_run(self):
        if bool(self.core.config.get("first_run", True)):
            util.LOG.info("首次运行：自动打开设置窗口（仅首次）")
            # 只要弹出过就不再自动弹出，避免每次开机骚扰
            self.core.config["first_run"] = False
            self.core.config.save()
            self.open_settings()

    def test_popup(self):
        self.core.inject_test_message()

    # ---------------- 开机自启 ----------------
    def _sync_autostart_action(self):
        """菜单弹出前把勾选状态同步成注册表的真实状态。"""
        action = self.actions.get("autostart")
        if action is None:
            return
        self._syncing_autostart = True
        try:
            action.setChecked(autostart.is_enabled())
        finally:
            self._syncing_autostart = False

    def toggle_autostart(self, checked):
        if self._syncing_autostart:
            return
        ok, message = autostart.apply(bool(checked))
        if not ok:
            self._notify(style.APP_TITLE, message, warning=True)
            self._sync_autostart_action()
            return
        self._notify(
            style.APP_TITLE,
            "{}\n{}".format(message, autostart.launch_command()),
        )
        # 设置窗口开着的话同步它的勾选框
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            try:
                self.settings_dialog.autostart_check.setChecked(bool(checked))
            except Exception:
                pass
        self._refresh_tray()

    def copy_address(self):
        try:
            QApplication.clipboard().setText(self.core.address)
            self._notify(style.APP_TITLE, "已复制访问地址：{}".format(self.core.address))
        except Exception:
            pass

    def open_web(self):
        QDesktopServices.openUrl(QUrl(self.core.address))

    def open_author(self):
        QDesktopServices.openUrl(QUrl(style.AUTHOR_URL))

    def quit(self):
        self.shutdown()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    # ---------------- 错误提示 ----------------
    def _show_fatal(self, message):
        try:
            QtMessageBox.critical(
                None, style.APP_TITLE,
                "服务无法启动：{}\n\n请在设置中更换监听端口后重试。".format(message),
            )
        except Exception:
            pass

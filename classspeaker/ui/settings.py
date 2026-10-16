# -*- coding: utf-8 -*-
"""设置面板。

同一套界面用在三个地方：
  * 独立版 / exe 版的托盘菜单「设置…」
  * 首次运行自动弹出一次
  * Class Widgets 插件设置页（CW 会实例化 `Settings(plugin_path)`）

因此基类是 QWidget 而不是 QDialog，且核心对象是**懒解析**的：
CW 会先构造设置页、后才调用 Plugin.execute()，这时核心还不存在。
"""
import os

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox as QtMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import autostart, config as config_mod, paths, util

from . import style
from .popup import MessageBox


class SettingsPanel(QWidget):
    saved = pyqtSignal(dict)

    def __init__(self, core=None, parent=None, core_provider=None):
        super(SettingsPanel, self).__init__(parent)
        self._core = core
        self._core_provider = core_provider
        self._fallback_config = None
        self._preview_popup = None
        self.setWindowTitle("{} · 设置".format(style.APP_TITLE))
        self.setWindowIcon(style.build_icon())
        self.setStyleSheet(style.dialog_stylesheet())
        self.setMinimumWidth(560)
        self._build_ui()
        self._load_values()

    # ---------------- 核心对象（可能晚于本窗口才创建）----------------
    @property
    def core(self):
        if self._core is None and self._core_provider is not None:
            try:
                self._core = self._core_provider()
            except Exception:
                self._core = None
        return self._core

    @property
    def config(self):
        core = self.core
        if core is not None:
            return core.config
        if self._fallback_config is None:
            self._fallback_config = config_mod.Config()
        return self._fallback_config

    # ---------------- 界面 ----------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel(style.APP_SUBTITLE, self)
        header.setObjectName("h1")
        layout.addWidget(header)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("hint")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        tabs = QTabWidget(self)
        tabs.addTab(self._tab_classroom(), "教室与网络")
        tabs.addTab(self._tab_popup(), "弹窗与声音")
        tabs.addTab(self._tab_account(), "账号")
        layout.addWidget(tabs, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        author_btn = QPushButton(style.AUTHOR_BUTTON_TEXT, self)
        author_btn.setObjectName("author")
        author_btn.setToolTip(style.AUTHOR_URL)
        author_btn.clicked.connect(self._open_author)
        bottom.addWidget(author_btn)

        data_btn = QPushButton("打开数据目录", self)
        data_btn.clicked.connect(self._open_data_dir)
        bottom.addWidget(data_btn)
        bottom.addStretch(1)

        save_btn = QPushButton("保存并应用", self)
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        bottom.addWidget(save_btn)

        close_btn = QPushButton("关闭", self)
        close_btn.clicked.connect(self.close)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

    def _tab_classroom(self):
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        ident = QGroupBox("教室标识", page)
        form = QFormLayout(ident)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)
        self.name_edit = QLineEdit(ident)
        self.name_edit.setPlaceholderText("留空则使用计算机名：{}".format(util.hostname()))
        form.addRow("教室显示名", self.name_edit)
        self.report_label = QLabel(ident)
        self.report_label.setObjectName("hint")
        self.report_label.setWordWrap(True)
        form.addRow("自动上报", self.report_label)
        copy_btn = QPushButton("复制访问地址", ident)
        copy_btn.clicked.connect(self._copy_address)
        open_btn = QPushButton("在浏览器中打开", ident)
        open_btn.clicked.connect(self._open_web)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(copy_btn)
        row.addWidget(open_btn)
        row.addStretch(1)
        holder = QWidget(ident)
        holder.setLayout(row)
        form.addRow("", holder)
        outer.addWidget(ident)

        network = QGroupBox("局域网服务", page)
        form2 = QFormLayout(network)
        form2.setLabelAlignment(Qt.AlignRight)
        form2.setSpacing(8)
        self.port_spin = QSpinBox(network)
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setToolTip("教师访问 http://本机IP:端口 即进入教师端")
        form2.addRow("监听端口", self.port_spin)
        self.approval_check = QCheckBox("新注册的教师账号需要管理员审批后登录", network)
        form2.addRow("", self.approval_check)
        self.service_label = QLabel(network)
        self.service_label.setObjectName("hint")
        self.service_label.setWordWrap(True)
        form2.addRow("服务状态", self.service_label)
        outer.addWidget(network)

        startup = QGroupBox("启动与后台运行", page)
        form3 = QFormLayout(startup)
        form3.setLabelAlignment(Qt.AlignRight)
        form3.setSpacing(8)
        self.autostart_check = QCheckBox(
            "开机自动启动（登录 Windows 后自动在后台运行，托盘图标常驻）", startup
        )
        if not autostart.supported():
            self.autostart_check.setEnabled(False)
            self.autostart_check.setToolTip("仅支持 Windows 注册表自启")
        form3.addRow("", self.autostart_check)
        self.autostart_label = QLabel(startup)
        self.autostart_label.setObjectName("hint")
        self.autostart_label.setWordWrap(True)
        form3.addRow("自启命令", self.autostart_label)
        outer.addWidget(startup)
        outer.addStretch(1)
        return page

    def _tab_popup(self):
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        popup_group = QGroupBox("弹窗外观", page)
        form = QFormLayout(popup_group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)

        self.width_spin = QSpinBox(popup_group)
        self.width_spin.setRange(320, 3000)
        self.width_spin.setSuffix(" px")
        form.addRow("弹窗宽度", self.width_spin)

        self.height_spin = QSpinBox(popup_group)
        self.height_spin.setRange(200, 2000)
        self.height_spin.setSuffix(" px")
        form.addRow("弹窗高度", self.height_spin)

        self.font_spin = QSpinBox(popup_group)
        self.font_spin.setRange(12, 96)
        self.font_spin.setSuffix(" px")
        form.addRow("正文字体大小", self.font_spin)

        opacity_row = QWidget(popup_group)
        opacity_layout = QHBoxLayout(opacity_row)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.setSpacing(8)
        self.opacity_slider = QSlider(Qt.Horizontal, opacity_row)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_label = QLabel("96%", opacity_row)
        self.opacity_label.setMinimumWidth(46)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        form.addRow("窗口透明度", opacity_row)

        self.title_edit = QLineEdit(popup_group)
        self.title_edit.setPlaceholderText("{sender}老师发来的消息")
        form.addRow("标题模板", self.title_edit)

        self.drag_check = QCheckBox("允许拖动弹窗位置（不能关闭，只能确认）", popup_group)
        form.addRow("", self.drag_check)

        self.force_top_check = QCheckBox("未确认前保持置顶（每 2 秒重新置顶一次）", popup_group)
        form.addRow("", self.force_top_check)
        outer.addWidget(popup_group)

        sound_group = QGroupBox("提示音", page)
        form2 = QFormLayout(sound_group)
        form2.setLabelAlignment(Qt.AlignRight)
        form2.setSpacing(8)
        self.sound_check = QCheckBox("消息弹出时播放提示音（默认关闭）", sound_group)
        form2.addRow("", self.sound_check)

        sound_row = QWidget(sound_group)
        sound_layout = QHBoxLayout(sound_row)
        sound_layout.setContentsMargins(0, 0, 0, 0)
        sound_layout.setSpacing(8)
        self.sound_edit = QLineEdit(sound_row)
        self.sound_edit.setPlaceholderText("留空则使用自带声音：{}".format(paths.DEFAULT_SOUND))
        browse_btn = QPushButton("浏览…", sound_row)
        browse_btn.clicked.connect(self._choose_sound)
        preview_btn = QPushButton("试听", sound_row)
        preview_btn.clicked.connect(self._preview_sound)
        reset_btn = QPushButton("用自带的", sound_row)
        reset_btn.clicked.connect(lambda: self.sound_edit.setText(""))
        sound_layout.addWidget(self.sound_edit, 1)
        sound_layout.addWidget(browse_btn)
        sound_layout.addWidget(preview_btn)
        sound_layout.addWidget(reset_btn)
        form2.addRow("声音文件", sound_row)

        self.repeat_spin = QSpinBox(sound_group)
        self.repeat_spin.setRange(1, 10)
        self.repeat_spin.setSuffix(" 次")
        form2.addRow("重复播放", self.repeat_spin)
        outer.addWidget(sound_group)

        test_row = QHBoxLayout()
        test_btn = QPushButton("测试弹窗", page)
        test_btn.setObjectName("primary")
        test_btn.clicked.connect(self._test_popup)
        test_row.addWidget(test_btn)
        test_row.addWidget(QLabel("按当前窗口中的设置立即预览效果", page))
        test_row.addStretch(1)
        outer.addLayout(test_row)
        outer.addStretch(1)
        return page

    def _tab_account(self):
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        group = QGroupBox("管理员账号（admin）", page)
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)
        hint = QLabel(
            "内置管理员账号用于审批教师注册申请。\n"
            "初始账号：admin　初始密码：admin123\n"
            "首次使用后请务必修改密码。",
            group,
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        form.addRow("", hint)

        self.admin_pwd_edit = QLineEdit(group)
        self.admin_pwd_edit.setEchoMode(QLineEdit.Password)
        self.admin_pwd_edit.setPlaceholderText("输入新的管理员密码（至少 6 位）")
        form.addRow("重置密码", self.admin_pwd_edit)

        reset_btn = QPushButton("重置管理员密码", group)
        reset_btn.clicked.connect(self._reset_admin_password)
        form.addRow("", reset_btn)

        self.user_stats = QLabel(group)
        self.user_stats.setObjectName("hint")
        self.user_stats.setWordWrap(True)
        form.addRow("账号统计", self.user_stats)
        outer.addWidget(group)
        outer.addStretch(1)
        return page

    # ---------------- 数据装载/收集 ----------------
    def _load_values(self):
        cfg = self.config
        self.name_edit.setText(cfg.get("classroom_name") or "")
        self.port_spin.setValue(cfg.port)
        self.approval_check.setChecked(bool(cfg.get("require_approval", True)))
        width, height = cfg.popup_size
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.font_spin.setValue(cfg.popup_font_size)
        self.opacity_slider.setValue(int(round(cfg.popup_opacity * 100)))
        self.title_edit.setText(cfg.get("popup_title_template") or "")
        self.drag_check.setChecked(bool(cfg.get("popup_allow_drag", True)))
        self.force_top_check.setChecked(bool(cfg.get("popup_force_top", True)))
        self.sound_check.setChecked(cfg.sound_enabled)
        self.sound_edit.setText(cfg.get("sound_path") or "")
        self.repeat_spin.setValue(cfg.sound_repeat)
        self._refresh_info()

    def _collect(self):
        return {
            "classroom_name": self.name_edit.text().strip(),
            "port": int(self.port_spin.value()),
            "require_approval": bool(self.approval_check.isChecked()),
            "popup_width": int(self.width_spin.value()),
            "popup_height": int(self.height_spin.value()),
            "popup_font_size": int(self.font_spin.value()),
            "popup_opacity": float(self.opacity_slider.value()) / 100.0,
            "popup_title_template": self.title_edit.text().strip()
                                    or "{sender}老师发来的消息",
            "popup_allow_drag": bool(self.drag_check.isChecked()),
            "popup_force_top": bool(self.force_top_check.isChecked()),
            "sound_enabled": bool(self.sound_check.isChecked()),
            "sound_path": self.sound_edit.text().strip(),
            "sound_repeat": int(self.repeat_spin.value()),
        }

    def _refresh_info(self):
        ips = util.all_lan_ips()
        self.report_label.setText(
            "计算机名：{}\nIP 地址：{}\n访问地址：http://{}:{}".format(
                util.hostname(),
                "、".join(ips) if ips else "未检测到",
                ips[0] if ips else "127.0.0.1",
                self.port_spin.value(),
            )
        )
        core = self.core
        if core is None:
            self.service_label.setText("未运行（本窗口只是预览配置）")
        else:
            running = core.server.running
            self.service_label.setText(
                "{}　运行时长：{}　待确认消息：{} 条".format(
                    "运行中" if running else "未运行",
                    util.human_duration(core.uptime()),
                    core.pending_count(),
                )
            )
        self._refresh_autostart()
        try:
            store = core.store if core is not None else None
            if store is None:
                self.user_stats.setText("账号统计不可用（服务未启动）")
            else:
                pending = store.count_users("pending")
                total = store.count_users()
                self.user_stats.setText(
                    "共 {} 个账号，其中 {} 个等待审批".format(total, pending)
                )
        except Exception:
            self.user_stats.setText("账号统计不可用")

    def _refresh_autostart(self):
        """开机自启状态以注册表为准，不存进 config.json。"""
        if not autostart.supported():
            self.autostart_check.setChecked(False)
            self.autostart_label.setText("当前系统不支持（仅 Windows）")
            return
        self.autostart_check.setChecked(autostart.is_enabled())
        command = autostart.launch_command()
        registered = autostart.current_value()
        if registered and registered.strip() != command.strip():
            self.autostart_label.setText(
                "注册表里记录的是旧位置，保存后会修正为：\n{}".format(command)
            )
        else:
            self.autostart_label.setText(command)

    # ---------------- 交互 ----------------
    def _on_opacity_changed(self, value):
        self.opacity_label.setText("{}%".format(value))

    def _copy_address(self):
        from PyQt5.QtWidgets import QApplication

        address = "http://{}:{}".format(
            util.primary_lan_ip(), self.port_spin.value()
        )
        QApplication.clipboard().setText(address)
        self.status_label.setText("已复制访问地址：{}".format(address))

    def _open_web(self):
        QDesktopServices.openUrl(
            QUrl("http://127.0.0.1:{}".format(self.port_spin.value()))
        )

    def _open_author(self):
        QDesktopServices.openUrl(QUrl(style.AUTHOR_URL))

    def _open_data_dir(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(paths.DATA_DIR))

    def _choose_sound(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择提示音文件", self.sound_edit.text() or paths.ASSET_DIR,
            "音频文件 (*.wav *.mp3 *.wma *.ogg);;所有文件 (*.*)",
        )
        if path:
            self.sound_edit.setText(os.path.normpath(path))

    def _sound_file_for_preview(self):
        candidate = self.sound_edit.text().strip()
        if candidate and os.path.isfile(candidate):
            return candidate
        if os.path.isfile(paths.DEFAULT_SOUND):
            return paths.DEFAULT_SOUND
        return ""

    def _preview_sound(self):
        path = self._sound_file_for_preview()
        if not path:
            QtMessageBox.warning(self, "提示音", "没有可用的声音文件。")
            return
        try:
            import winsound

            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as exc:
            QtMessageBox.warning(self, "提示音", "播放失败：{}".format(exc))

    def _test_popup(self):
        values = self._collect()
        preview_config = self.config.clone(values)
        preview_config["sound_enabled"] = bool(self.sound_check.isChecked())
        if self._preview_popup is not None:
            try:
                self._preview_popup.deleteLater()
            except Exception:
                pass
        message = {
            "id": 0,
            "sender_name": "测试",
            "content": "这是一条测试消息：弹窗大小、字体、透明度、提示音都会按当前设置显示。",
            "created_at": util.now_str(),
        }
        popup = MessageBox(preview_config, message, None)
        popup.confirmed.connect(lambda _mid: None)
        self._preview_popup = popup
        popup.show()

    def _reset_admin_password(self):
        password = self.admin_pwd_edit.text().strip()
        if not password:
            QtMessageBox.information(self, "重置密码", "请先输入新的管理员密码。")
            return
        core = self.core
        if core is None:
            QtMessageBox.warning(self, "重置密码", "服务未启动，无法重置密码。")
            return
        ok, message = core.reset_admin_password(password)
        if ok:
            self.admin_pwd_edit.clear()
            QtMessageBox.information(self, "重置密码", message)
        else:
            QtMessageBox.warning(self, "重置密码", message)
        self._refresh_info()

    # ---------------- 保存 ----------------
    def _save(self):
        values = self._collect()
        old_port = self.config.port
        self.config.update(values)
        core = self.core
        if core is not None and values["port"] != old_port:
            ok, message = core.apply_port(values["port"])
            if not ok:
                QtMessageBox.warning(self, "端口", message)
        self.config["first_run"] = False
        self.config.save()

        auto_ok, auto_message = autostart.apply(
            bool(self.autostart_check.isChecked())
        )
        if not auto_ok:
            QtMessageBox.warning(self, "开机自启", auto_message)

        self.saved.emit(values)
        self._refresh_info()
        self.status_label.setText(
            "{}；弹窗在下一条消息生效，端口改变会立即重启服务。".format(auto_message)
        )

    def showEvent(self, event):
        super(SettingsPanel, self).showEvent(event)
        self._refresh_info()

    def closeEvent(self, event):
        # 关闭设置窗口同时把"首次运行"标记清掉
        try:
            self.config["first_run"] = False
            self.config.save()
        except Exception:
            pass
        super(SettingsPanel, self).closeEvent(event)


# 独立版 / 托盘沿用旧名字，避免调用处大改
SettingsDialog = SettingsPanel


class PluginSettings(SettingsPanel):
    """Class Widgets 插件设置页。

    CW 的 PluginLoader 会执行 `Settings(str(PLUGIN_HOME / 插件名))`，
    所以第一个参数必须是插件路径；核心对象晚点才由 Plugin.execute() 创建，
    这里用 core_provider 懒解析。
    """

    def __init__(self, plugin_path=None, parent=None):
        super(PluginSettings, self).__init__(
            core=None, parent=parent, core_provider=_current_core
        )
        self.PLUGIN_PATH = plugin_path or paths.EXE_DIR


def _current_core():
    """由 main.py 在创建核心后回填。"""
    return _CORE_HOLDER.get("core")


_CORE_HOLDER = {"core": None}


def set_current_core(core):
    _CORE_HOLDER["core"] = core

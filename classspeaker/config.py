# -*- coding: utf-8 -*-
"""配置读写（data/config.json）。"""
import os

from . import paths, util

DEFAULTS = {
    # ---- 教室标识 ----
    # 自定义显示名（留空则用主机名），教师端看到的教室名
    "classroom_name": "",
    # ---- 服务 ----
    "bind": "0.0.0.0",
    # 默认端口。刻意避开 8080（Docker/Tomcat 常占）和 Windows 保留段
    # （Hyper-V/WSL 会保留 10165-10264 这类区间）。被占用时启动会自动顺延。
    "port": 10265,
    "require_approval": True,        # 新账号是否需要管理员审批
    # ---- 弹窗 ----
    "popup_width": 640,
    "popup_height": 380,
    "popup_font_size": 26,
    "popup_opacity": 0.96,           # 0.2 ~ 1.0
    "popup_title_template": "{sender}老师发来的消息",
    "popup_force_top": True,         # 未确认时周期性置顶，防止被老师忽略
    "popup_allow_drag": True,
    # ---- 声音 ----
    "sound_enabled": False,          # 默认不开启
    "sound_path": "",                # 留空则使用自带 assets/notify.wav
    "sound_repeat": 1,
    # ---- 其他 ----
    "replay_pending_on_start": True,  # 程序重启后补弹未确认的消息
    "replay_hours": 12,               # 只补弹最近 N 小时内未确认的
    "show_tray_icon": True,
    "show_notification_on_start": True,
    "keep_days": 30,
    "first_run": True,
}


class Config(object):
    def __init__(self, path=None):
        self.path = path or paths.CONFIG_PATH
        self._data = dict(DEFAULTS)
        self._explicit = set()
        self.load()

    # ---------- 基础读写 ----------
    def load(self):
        raw = util.read_json(self.path, {})
        if not isinstance(raw, dict):
            raw = {}
        merged = dict(DEFAULTS)
        merged.update(raw)
        self._data = merged
        self._explicit = set(raw.keys())
        return self._data

    def has_explicit(self, key):
        """用户是否在 config.json 里显式写过这一项（用来区分"默认值"与"用户选择"）。"""
        return key in self._explicit

    def save(self):
        util.write_json_atomic(self.path, self._data)

    def as_dict(self):
        return dict(self._data)

    def update(self, values):
        for key, value in (values or {}).items():
            if key in DEFAULTS or key in self._data:
                self._data[key] = value
                self._explicit.add(key)
        self.save()

    def clone(self, values=None):
        """返回一个临时副本（不落盘），用于"测试弹窗"等预览场景。"""
        other = Config.__new__(Config)
        other.path = self.path
        other._data = dict(self._data)
        for key, value in (values or {}).items():
            other._data[key] = value
        return other

    def get(self, key, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self._data[key] = value

    def typed(self, key, caster, default=None):
        try:
            return caster(self.get(key, default))
        except Exception:
            return default if default is not None else DEFAULTS.get(key)

    # ---------- 语义化取值 ----------
    @property
    def port(self):
        port = self.typed("port", int, 8080)
        if port < 1 or port > 65535:
            port = 8080
        return port

    @property
    def bind(self):
        value = (self.get("bind") or "0.0.0.0").strip()
        return value or "0.0.0.0"

    @property
    def classroom_name(self):
        """自定义名称优先，否则用主机名。"""
        name = (self.get("classroom_name") or "").strip()
        return name or util.hostname()

    @property
    def popup_size(self):
        width = max(320, self.typed("popup_width", int, 640))
        height = max(200, self.typed("popup_height", int, 380))
        return width, height

    @property
    def popup_font_size(self):
        return max(12, min(96, self.typed("popup_font_size", int, 26)))

    @property
    def popup_opacity(self):
        try:
            value = float(self.get("popup_opacity", 0.96))
        except Exception:
            value = 0.96
        return max(0.3, min(1.0, value))

    @property
    def sound_enabled(self):
        return bool(self.get("sound_enabled", False))

    @property
    def sound_repeat(self):
        return max(1, min(10, self.typed("sound_repeat", int, 1)))

    def sound_file(self):
        """返回实际可用的声音文件路径；没有则返回空串。"""
        candidate = (self.get("sound_path") or "").strip().strip('"')
        if candidate and os.path.isfile(candidate):
            return candidate
        if os.path.isfile(paths.DEFAULT_SOUND):
            return paths.DEFAULT_SOUND
        return ""

    @property
    def address(self):
        return "http://{}:{}".format(util.primary_lan_ip(), self.port)

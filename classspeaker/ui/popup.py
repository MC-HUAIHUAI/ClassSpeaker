# -*- coding: utf-8 -*-
"""教室端弹窗：无边框、置顶、只能通过"确认收到"关闭。"""
from PyQt5.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QColor

from . import style

SOUND_INTERVAL_MS = 2600


class MessageBox(QWidget):
    """一条消息对应一个弹窗。只有点击"确认收到"才会关闭。"""

    confirmed = pyqtSignal(int)

    def __init__(self, config, message, parent=None):
        super(MessageBox, self).__init__(parent)
        self.config = config
        self.message = message or {}
        self._confirmed = False
        self._drag_offset = None
        self._plays_left = 0
        self._sound_timer = QTimer(self)
        self._sound_timer.setInterval(SOUND_INTERVAL_MS)
        self._sound_timer.timeout.connect(self._play_sound_once)
        self._top_timer = QTimer(self)
        self._top_timer.setInterval(2000)
        self._top_timer.timeout.connect(self._keep_on_top)

        self._build_ui()
        self._apply_geometry()
        self._start_sound()

    # ---------------- 构建界面 ----------------
    def _build_ui(self):
        self.setObjectName("root")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(style.APP_TITLE)
        self.setWindowIcon(style.build_icon())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(0)

        card = QFrame(self)
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(card)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 110))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        badge = QLabel("教室小喇叭", card)
        badge.setObjectName("badge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        header.addWidget(badge)
        header.addStretch(1)
        layout.addLayout(header)

        title = QLabel(self._title_text(), card)
        title.setObjectName("title")
        title.setWordWrap(True)
        layout.addWidget(title)

        content = QLabel(self.message.get("content") or "", card)
        content.setObjectName("content")
        content.setWordWrap(True)
        content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        content.setTextInteractionFlags(Qt.NoTextInteraction)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(content, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        sent_at = QLabel("发送时间：{}".format(self.message.get("created_at") or "-"), card)
        sent_at.setObjectName("time")
        footer.addWidget(sent_at)
        footer.addStretch(1)
        self.confirm_btn = QPushButton("确认收到", card)
        self.confirm_btn.setObjectName("confirmBtn")
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.clicked.connect(self.confirm)
        footer.addWidget(self.confirm_btn)
        layout.addLayout(footer)

        self.setStyleSheet(style.popup_stylesheet(self.config.popup_font_size))
        self.setWindowOpacity(self.config.popup_opacity)

    def _title_text(self):
        template = self.config.get("popup_title_template") or "{sender}老师发来的消息"
        sender = (self.message.get("sender_name") or "老师").strip()
        try:
            return template.format(sender=sender)
        except Exception:
            return "{}老师发来的消息".format(sender)

    # ---------------- 位置与尺寸 ----------------
    def _apply_geometry(self):
        width, height = self.config.popup_size
        self.resize(width, height)

        screen = QGuiApplication.primaryScreen()
        try:
            widget_screen = QApplication.screenAt(self.pos())
            if widget_screen is not None:
                screen = widget_screen
        except Exception:
            pass
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.x() + max(0, (area.width() - self.width()) // 2)
        y = area.y() + max(0, (area.height() - self.height()) // 2)
        self.move(QPoint(x, y))

    # ---------------- 声音 ----------------
    def _start_sound(self):
        if not self.config.sound_enabled:
            return
        if not self.config.sound_file():
            return
        self._plays_left = self.config.sound_repeat
        self._play_sound_once()
        if self._plays_left > 0:
            self._sound_timer.start()

    def _play_sound_once(self):
        if self._plays_left <= 0:
            self._sound_timer.stop()
            return
        self._plays_left -= 1
        path = self.config.sound_file()
        if not path:
            self._sound_timer.stop()
            return
        played = False
        try:
            import winsound

            winsound.PlaySound(
                path, winsound.SND_FILENAME | winsound.SND_ASYNC
            )
            played = True
        except Exception:
            played = False
        if not played:
            try:
                QApplication.beep()
            except Exception:
                pass
        if self._plays_left <= 0:
            self._sound_timer.stop()

    def stop_sound(self):
        self._sound_timer.stop()
        self._plays_left = 0
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    # ---------------- 置顶 ----------------
    def _keep_on_top(self):
        if self._confirmed or not self.isVisible():
            return
        try:
            self.raise_()
        except Exception:
            pass

    # ---------------- 确认 ----------------
    def confirm(self):
        if self._confirmed:
            return
        self._confirmed = True
        self.stop_sound()
        self._top_timer.stop()
        self.hide()
        try:
            self.confirmed.emit(int(self.message.get("id") or 0))
        finally:
            self.deleteLater()

    # ---------------- 事件屏蔽 ----------------
    def closeEvent(self, event):
        # 只能通过"确认收到"关闭，Alt+F4 / 系统关闭一律忽略
        if self._confirmed:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_F4) and \
                event.modifiers() & Qt.AltModifier:
            event.ignore()
            return
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return
        super(MessageBox, self).keyPressEvent(event)

    def reject(self):
        # 屏蔽 Esc 触发的关闭
        pass

    # ---------------- 拖动 ----------------
    def mousePressEvent(self, event):
        if not self.config.get("popup_allow_drag", True):
            return
        if event.button() == Qt.LeftButton and event.pos().y() < 96:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is None:
            return
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        event.accept()

    # ---------------- 显示 ----------------
    def showEvent(self, event):
        super(MessageBox, self).showEvent(event)
        if self.config.get("popup_force_top", True):
            self._top_timer.start()
        try:
            self.raise_()
            self.activateWindow()
            self.confirm_btn.setFocus()
        except Exception:
            pass

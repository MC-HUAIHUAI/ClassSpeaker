# -*- coding: utf-8 -*-
"""界面样式与图标（全部代码生成，不依赖外部图片资源）。"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

APP_TITLE = "教室小喇叭"
APP_SUBTITLE = "教室端 · 局域网消息播报"
AUTHOR_URL = "https://space.bilibili.com/1437520017"
AUTHOR_BUTTON_TEXT = "为作者充电"

BRAND = "#2f6fed"
BRAND_DARK = "#24509f"
BRAND_LIGHT = "#e8f0ff"

FONT_FAMILY = '"Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif'


def build_icon(size=64):
    """画一个喇叭图标（免外部图片）。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    radius = size * 0.22
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(BRAND)))
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    white = QColor("#ffffff")
    # 喇叭主体（梯形）
    body = QPainterPath()
    body.moveTo(size * 0.22, size * 0.40)
    body.lineTo(size * 0.38, size * 0.40)
    body.lineTo(size * 0.56, size * 0.24)
    body.lineTo(size * 0.56, size * 0.76)
    body.lineTo(size * 0.38, size * 0.60)
    body.lineTo(size * 0.22, size * 0.60)
    body.closeSubpath()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(white))
    painter.drawPath(body)

    # 声波（两圈右向圆弧）
    pen = QPen(white)
    pen.setWidthF(max(1.5, size * 0.05))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    for radius in (0.11, 0.21):
        rect = QRectF(size * (0.56 - radius), size * (0.5 - radius),
                      size * 2.0 * radius, size * 2.0 * radius)
        painter.drawArc(rect, -58 * 16, 116 * 16)

    painter.end()
    return QIcon(pixmap)


def popup_stylesheet(font_size):
    content = max(14, int(font_size))
    title = max(13, int(font_size * 0.62))
    meta = max(12, int(font_size * 0.46))
    button = max(15, int(font_size * 0.66))
    return """
QWidget#root { background: transparent; }
QFrame#card {
    background: rgba(255, 255, 255, 0.985);
    border: 3px solid %(brand)s;
    border-radius: 20px;
}
QLabel#badge {
    background: %(brand_light)s;
    color: %(brand)s;
    border-radius: 10px;
    padding: 3px 12px;
    font-family: %(font)s;
    font-size: %(meta)spx;
    font-weight: bold;
}
QLabel#title {
    color: %(brand)s;
    font-family: %(font)s;
    font-size: %(title)spx;
    font-weight: bold;
}
QLabel#content {
    color: #16181d;
    font-family: %(font)s;
    font-size: %(content)spx;
}
QLabel#time {
    color: #8b8f98;
    font-family: %(font)s;
    font-size: %(meta)spx;
}
QPushButton#confirmBtn {
    background: %(brand)s;
    color: #ffffff;
    border: none;
    border-radius: 12px;
    padding: 12px 40px;
    font-family: %(font)s;
    font-size: %(button)spx;
    font-weight: bold;
}
QPushButton#confirmBtn:hover { background: #3f7bf0; }
QPushButton#confirmBtn:pressed { background: %(brand_dark)s; }
""" % {
        "brand": BRAND,
        "brand_dark": BRAND_DARK,
        "brand_light": BRAND_LIGHT,
        "font": FONT_FAMILY,
        "content": content,
        "title": title,
        "meta": meta,
        "button": button,
    }


def dialog_stylesheet():
    """设置面板样式。

    注意：所有选择器都以 ``#settingsRoot`` 开头。这是必需的 —— 宿主
    （Class Widgets 2）会往 QApplication 上挂全局深色样式，像
    ``QGroupBox QLabel { color: white }`` 这种比单个 ``QLabel`` 更具体，
    会把我们浅色面板里的文字刷成白色（白底白字，看不见）。
    加 id 前缀后（id 权重 100 > 类型 1）稳定压过宿主的全局样式。
    """
    return """
QWidget#settingsRoot { background: #f5f6f8; }

QWidget#settingsRoot QLabel {
    font-family: %(font)s;
    font-size: 13px;
    color: #2b2f36;
}
QWidget#settingsRoot QLabel#h1 {
    font-size: 16px;
    font-weight: bold;
    color: #16181d;
}
QWidget#settingsRoot QLabel#hint {
    color: #6f7580;
    font-size: 12px;
}

QWidget#settingsRoot QWidget#tabPage { background: #ffffff; }
QWidget#settingsRoot QScrollArea { background: #ffffff; border: none; }

QWidget#settingsRoot QGroupBox {
    font-family: %(font)s;
    font-size: 13px;
    font-weight: bold;
    color: #2b2f36;
    border: 1px solid #dcdfe6;
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px 12px 10px 12px;
    background: #ffffff;
}
QWidget#settingsRoot QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #2b2f36;
    background: #ffffff;
}

QWidget#settingsRoot QLineEdit,
QWidget#settingsRoot QSpinBox,
QWidget#settingsRoot QComboBox,
QWidget#settingsRoot QPlainTextEdit {
    font-family: %(font)s;
    font-size: 13px;
    color: #16181d;
    background: #ffffff;
    border: 1px solid #cfd4dc;
    border-radius: 8px;
    padding: 5px 8px;
    min-height: 20px;
    selection-background-color: %(brand)s;
    selection-color: #ffffff;
}
QWidget#settingsRoot QLineEdit:focus,
QWidget#settingsRoot QSpinBox:focus,
QWidget#settingsRoot QComboBox:focus {
    border: 1px solid %(brand)s;
}
QWidget#settingsRoot QLineEdit[readOnly="true"] {
    background: #f1f3f6;
    color: #6b7280;
}
QWidget#settingsRoot QComboBox QAbstractItemView {
    background: #ffffff;
    color: #16181d;
    selection-background-color: %(brand)s;
    selection-color: #ffffff;
}

QWidget#settingsRoot QCheckBox {
    font-family: %(font)s;
    font-size: 13px;
    color: #2b2f36;
    spacing: 8px;
    background: transparent;
}

QWidget#settingsRoot QPushButton {
    font-family: %(font)s;
    font-size: 13px;
    color: #2b2f36;
    background: #ffffff;
    border: 1px solid #cfd4dc;
    border-radius: 8px;
    padding: 6px 16px;
}
QWidget#settingsRoot QPushButton:hover {
    border-color: %(brand)s;
    color: %(brand)s;
}
QWidget#settingsRoot QPushButton#primary {
    background: %(brand)s;
    color: #ffffff;
    border: none;
    font-weight: bold;
}
QWidget#settingsRoot QPushButton#primary:hover { background: #3f7bf0; }
QWidget#settingsRoot QPushButton#primary:pressed { background: %(brand_dark)s; }
QWidget#settingsRoot QPushButton#author {
    border: 1px dashed %(brand)s;
    color: %(brand)s;
}

QWidget#settingsRoot QSlider::groove:horizontal {
    height: 6px;
    background: #e2e5ea;
    border-radius: 3px;
}
QWidget#settingsRoot QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: %(brand)s;
}

QWidget#settingsRoot QTabWidget::pane {
    border: 1px solid #dcdfe6;
    border-radius: 10px;
    background: #ffffff;
}
QWidget#settingsRoot QTabBar::tab {
    font-family: %(font)s;
    font-size: 13px;
    color: #4b515a;
    background: #e9edf3;
    padding: 7px 18px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}
QWidget#settingsRoot QTabBar::tab:selected {
    background: %(brand)s;
    color: #ffffff;
}
QWidget#settingsRoot QTabBar::tab:hover:!selected { background: #dfe6f0; }

QWidget#settingsRoot QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QWidget#settingsRoot QScrollBar::handle:vertical {
    background: #c6ccd6;
    border-radius: 5px;
    min-height: 28px;
}
QWidget#settingsRoot QScrollBar::handle:vertical:hover { background: #aab2bf; }
QWidget#settingsRoot QScrollBar::add-line:vertical,
QWidget#settingsRoot QScrollBar::sub-line:vertical { height: 0; }
""" % {"font": FONT_FAMILY, "brand": BRAND, "brand_dark": BRAND_DARK}


def app_font(size=9):
    font = QFont("Microsoft YaHei UI")
    font.setPointSize(size)
    return font

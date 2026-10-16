# -*- coding: utf-8 -*-
"""界面样式与图标（全部代码生成，不依赖外部图片资源）。"""
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import (
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
    return """
QDialog { background: #f5f6f8; }
QLabel { font-family: %(font)s; font-size: 13px; color: #2b2f36; }
QLabel#h1 { font-size: 17px; font-weight: bold; color: #16181d; }
QLabel#hint { color: #7d838d; font-size: 12px; }
QLabel#fieldLabel { color: #4b515a; }
QGroupBox {
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
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit {
    font-family: %(font)s;
    font-size: 13px;
    border: 1px solid #cfd4dc;
    border-radius: 8px;
    padding: 5px 8px;
    background: #ffffff;
    min-height: 20px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid %(brand)s; }
QLineEdit[readOnly="true"] { background: #f1f3f6; color: #6b7280; }
QPushButton {
    font-family: %(font)s;
    font-size: 13px;
    border: 1px solid #cfd4dc;
    border-radius: 8px;
    padding: 6px 16px;
    background: #ffffff;
}
QPushButton:hover { border-color: %(brand)s; color: %(brand)s; }
QPushButton#primary {
    background: %(brand)s; color: #ffffff; border: none; font-weight: bold;
}
QPushButton#primary:hover { background: #3f7bf0; }
QPushButton#primary:pressed { background: %(brand_dark)s; }
QPushButton#author { border: 1px dashed %(brand)s; color: %(brand)s; }
QCheckBox { font-family: %(font)s; font-size: 13px; color: #2b2f36; spacing: 8px; }
QSlider::groove:horizontal { height: 6px; background: #e2e5ea; border-radius: 3px; }
QSlider::handle:horizontal {
    width: 16px; margin: -6px 0; border-radius: 8px; background: %(brand)s;
}
QTabWidget::pane { border: 1px solid #dcdfe6; border-radius: 10px; background: #ffffff; }
QTabBar::tab {
    font-family: %(font)s; font-size: 13px; padding: 7px 18px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}
QTabBar::tab:selected { background: %(brand)s; color: #ffffff; }
""" % {"font": FONT_FAMILY, "brand": BRAND, "brand_dark": BRAND_DARK}


def app_font(size=9):
    font = QFont("Microsoft YaHei UI")
    font.setPointSize(size)
    return font

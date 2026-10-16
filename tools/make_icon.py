# -*- coding: utf-8 -*-
"""生成程序图标 classspeaker/assets/app.ico（打包 exe 用）。

    set QT_QPA_PLATFORM=offscreen
    python tools/make_icon.py

用 PyQt5 画出喇叭图标，再手工拼一个 ICO 容器（内嵌 PNG，Vista 以上原生支持），
这样不依赖任何额外的图片转换库。
"""
import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtCore import QBuffer, QIODevice  # noqa: E402
from PyQt5.QtGui import QGuiApplication  # noqa: E402

from classspeaker.ui import style  # noqa: E402

SIZES = (256, 128, 64, 48, 32, 16)


def png_bytes(size):
    icon = style.build_icon(size)
    pixmap = icon.pixmap(size, size)
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    data = bytes(buffer.data())
    buffer.close()
    return data


def build_ico(entries):
    """entries: [(size, png_bytes), ...] -> 完整 ICO 字节"""
    count = len(entries)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    directory = b""
    payload = b""
    for size, data in entries:
        dimension = 0 if size >= 256 else size
        directory += struct.pack(
            "<BBBBHHII",
            dimension, dimension, 0, 0, 1, 32, len(data), offset,
        )
        payload += data
        offset += len(data)
    return header + directory + payload


def main():
    argv = sys.argv[1:]
    app = QGuiApplication(sys.argv)  # noqa: F841 - QPixmap 需要 QGuiApplication
    target = os.path.join(ROOT, "classspeaker", "assets", "app.ico")
    entries = []
    for size in SIZES:
        data = png_bytes(size)
        if not data:
            continue
        entries.append((size, data))
    if not entries:
        print("生成失败：没有拿到任何图标数据")
        return 1
    with open(target, "wb") as fh:
        fh.write(build_ico(entries))
    print("已生成图标：{}（{} 字节，含 {} 种尺寸）".format(
        target, os.path.getsize(target), len(entries)))

    if "--preview" in argv:
        import tempfile

        preview = os.path.join(tempfile.gettempdir(), "classspeaker_icon_preview.png")
        with open(preview, "wb") as fh:
            fh.write(png_bytes(256))
        print("预览图：{}".format(preview))
    return 0


if __name__ == "__main__":
    sys.exit(main())

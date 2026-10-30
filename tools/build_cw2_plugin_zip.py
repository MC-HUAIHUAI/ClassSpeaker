# -*- coding: utf-8 -*-
"""打包 Class Widgets 2 插件：产出可被 CW2「导入」的 .cwplugin 归档。

    python tools\\build_cw2_plugin_zip.py
    python tools\\build_cw2_plugin_zip.py --out out

产物：dist\\ClassSpeaker-<版本>.cwplugin
（本质是 zip；CW2 的「设置 → 插件 → 导入」直接吃这个文件。）

归档结构（CW2 的 PluginArchiveInstaller 要求）：

    ClassSpeaker/
    ├─ cwplugin.json      ← 有且仅有 1 个，且所有文件都在它的同级/子目录下
    ├─ plugin.py
    ├─ icon.png
    ├─ README.md
    └─ classspeaker/...

安装后 CW2 会把目录名改成 plugin id（com.mchuaihuai.classspeaker）。
"""
import argparse
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "cw2", "ClassSpeaker")

EXCLUDE_DIRS = {"data", "__pycache__", ".git", "build", "dist", "libs"}
EXCLUDE_EXT = {".pyc", ".pyo"}
ARC_ROOT = "ClassSpeaker"


def read_version():
    try:
        with open(os.path.join(SOURCE, "cwplugin.json"), encoding="utf-8") as fh:
            return json.load(fh).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def collect():
    items = []
    for current, dirs, files in os.walk(SOURCE):
        dirs[:] = [d for d in dirs
                   if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for name in files:
            if os.path.splitext(name)[1].lower() in EXCLUDE_EXT:
                continue
            full = os.path.join(current, name)
            rel = os.path.relpath(full, SOURCE).replace("\\", "/")
            items.append((full, "{}/{}".format(ARC_ROOT, rel)))
    return items


def main(argv=None):
    parser = argparse.ArgumentParser(description="打包 Class Widgets 2 插件")
    parser.add_argument("--out", default=os.path.join(ROOT, "dist"))
    parser.add_argument("--version", default="")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if not os.path.isfile(os.path.join(SOURCE, "cwplugin.json")):
        print("[错误] 找不到 {} 下的 cwplugin.json".format(SOURCE))
        return 1

    version = args.version or read_version()
    os.makedirs(args.out, exist_ok=True)
    target = os.path.join(
        args.out, "ClassSpeaker-{}.cwplugin".format(version))

    items = collect()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, name in items:
            archive.write(source, name)

    print("已生成：{}（{:.1f} KB，{} 个文件）".format(
        target, os.path.getsize(target) / 1024.0, len(items)))
    print("用法：CW2 →「设置 → 插件 → 导入」，选这个 .cwplugin 文件即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""把插件打包成 zip：解压到 Class Widgets 的 plugins 目录即可使用。

    python tools\\build_plugin_zip.py
    python tools\\build_plugin_zip.py --out out      # 指定输出目录

产物：dist\\ClassSpeaker-<版本>-cw-plugin.zip
zip 内顶层就是 ClassSpeaker\\ ，所以用户直接把它解压到
    <ClassWidgets>\\plugins\\
即可（__init__.py / main.py / plugin.json / classspeaker\\ 都会就位）。

只打插件真正需要的文件，不包含 data\\（账号库）、tools\\、独立版入口。
"""
import argparse
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INCLUDE_FILES = ["__init__.py", "main.py", "plugin.json", "README.md"]
INCLUDE_DIRS = ["classspeaker"]
EXCLUDE_DIRS = {"data", "__pycache__", ".git", ".github", "build", "build32",
                "dist", "dist32", "installer", "tools", ".idea", ".vscode"}
EXCLUDE_EXT = {".pyc", ".pyo"}
ARC_ROOT = "ClassSpeaker"


def read_version():
    try:
        with open(os.path.join(ROOT, "plugin.json"), encoding="utf-8") as fh:
            return json.load(fh).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def collect():
    """返回 [(磁盘路径, zip 内路径)]。"""
    items = []
    for name in INCLUDE_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            items.append((path, "{}/{}".format(ARC_ROOT, name)))
    for folder in INCLUDE_DIRS:
        base = os.path.join(ROOT, folder)
        if not os.path.isdir(base):
            continue
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs
                       if d not in EXCLUDE_DIRS and not d.startswith(".")]
            for name in files:
                if os.path.splitext(name)[1].lower() in EXCLUDE_EXT:
                    continue
                full = os.path.join(current, name)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                items.append((full, "{}/{}".format(ARC_ROOT, rel)))
    return items


def main(argv=None):
    parser = argparse.ArgumentParser(description="打包 Class Widgets 插件 zip")
    parser.add_argument("--out", default=os.path.join(ROOT, "dist"))
    parser.add_argument("--version", default="")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    version = args.version or read_version()
    os.makedirs(args.out, exist_ok=True)
    target = os.path.join(
        args.out, "ClassSpeaker-{}-cw-plugin.zip".format(version))

    items = collect()
    if not any(path.endswith("plugin.json") for _f, path in items):
        print("[错误] 没找到 plugin.json，打包中止")
        return 1

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, name in items:
            archive.write(source, name)

    size = os.path.getsize(target)
    print("已生成：{}（{:.1f} KB，{} 个文件）".format(
        target, size / 1024.0, len(items)))
    print("用法：把它解压到 <ClassWidgets>\\plugins\\ 下，重启 Class Widgets 即可。")
    for _source, name in items:
        print("  " + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

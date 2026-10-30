# -*- coding: utf-8 -*-
"""按 CW2 的 PluginArchiveInstaller 规则校验 .cwplugin 归档（不启动 CW2）。

    python tools/cw2_archive_test.py dist\\ClassSpeaker-2.0.0.cwplugin
"""
import json
import os
import sys
import zipfile
from pathlib import PurePosixPath

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  [PASS] {}{}".format(name, ("  " + detail) if detail else ""))
    else:
        FAILED.append(name)
        print("  [FAIL] {}{}".format(name, ("  " + detail) if detail else ""))


def safe_path(name):
    if not name or "\x00" in name:
        return None
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        return None
    return path


def main():
    if len(sys.argv) < 2:
        print("用法: cw2_archive_test.py <file.cwplugin>")
        return 2
    target = sys.argv[1]

    print("\n== 归档基础 ==")
    check("文件存在", os.path.isfile(target), target)
    check("是 zip", zipfile.is_zipfile(target))
    check("大小 < 100MB", os.path.getsize(target) < 100 * 1024 * 1024,
          "{:.1f} KB".format(os.path.getsize(target) / 1024.0))

    with zipfile.ZipFile(target) as archive:
        members = archive.infolist()
        print("\n== 成员校验 ==")
        check("成员数 1~10000", 1 <= len(members) <= 10000, str(len(members)))
        check("没有符号链接",
              all(((m.external_attr >> 16) & 0xF000) != 0xA000 for m in members))
        bad = [m.filename for m in members if safe_path(m.filename) is None]
        check("所有路径安全（无绝对路径 / ..）", not bad, str(bad[:3]))

        manifests = [m.filename for m in members
                     if not m.is_dir()
                     and PurePosixPath(m.filename).name == "cwplugin.json"]
        print("\n== 清单 ==")
        check("有且仅有 1 个 cwplugin.json", len(manifests) == 1, str(manifests))
        manifest_member = manifests[0]
        root = PurePosixPath(manifest_member).parent

        outside = []
        for m in members:
            try:
                PurePosixPath(m.filename).relative_to(root)
            except ValueError:
                outside.append(m.filename)
        check("所有文件都在清单所在目录内", not outside, str(outside[:3]))

        manifest = json.loads(archive.read(manifest_member).decode("utf-8"))
        check("清单是对象", isinstance(manifest, dict))
        for field in ("id", "name", "version", "api_version", "entry", "author"):
            value = manifest.get(field)
            check("{} 为非空字符串".format(field),
                  isinstance(value, str) and bool(value.strip()), str(value))

        try:
            from packaging.version import Version

            Version(manifest["version"])
            check("version 是合法 PEP440", True, manifest["version"])
        except Exception as exc:
            check("version 是合法 PEP440", False, str(exc))

        check("id 不含非法字符",
              not any(c in manifest["id"] for c in '<>:"|?*\"'),
              manifest["id"])

        entry_member = "{}/{}".format(root, manifest["entry"]).replace("\\", "/")
        check("entry 文件在归档里", entry_member in [m.filename for m in members],
              entry_member)

        print("\n== 关键文件 ==")
        names = [m.filename for m in members]
        for need in ("plugin.py", "cwplugin.json", "icon.png",
                     "classspeaker/server.py", "classspeaker/web/index.html"):
            check("包含 {}".format(need),
                  "{}/{}".format(root, need) in names)

    print("\n================ 结果 ================")
    print("通过 {} 项，失败 {} 项".format(len(PASSED), len(FAILED)))
    if FAILED:
        for name in FAILED:
            print(" - 失败：{}".format(name))
        return 1
    print("全部通过 ✔（CW2 的导入器应该能接受）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

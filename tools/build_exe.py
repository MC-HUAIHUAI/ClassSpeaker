# -*- coding: utf-8 -*-
"""把教室小喇叭打包成 exe（支持 32 位 / 64 位）。

    python tools\\build_exe.py                     # 64 位单文件 -> dist\\ClassSpeaker.exe
    python tools\\build_exe.py --arch 32           # 32 位单文件 -> dist32\\ClassSpeaker.exe
    python tools\\build_exe.py --arch 32 --onedir  # 32 位目录版（启动更快）
    python tools\\build_exe.py --python C:\\Python38\\python.exe --dist out

说明：
  * 32 位 exe 在 32 位和 64 位 Windows 上都能跑；64 位 exe 只能跑在 64 位 Windows 上。
  * web/ 与 assets/ 打进 exe，运行时从 sys._MEIPASS 读取；
  * data/ 写在 exe 旁边的 data 子目录（不可写时退到 %LOCALAPPDATA%\\ClassSpeaker）；
  * --windowed 无控制台窗口，日志在 data/server.log。
"""
import argparse
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEP = os.pathsep  # Windows 上是 ';'

DEFAULT_PYTHON = {
    32: r"C:\Python314-32\python.exe",
    64: r"C:\Python314\python.exe",
}
DEFAULT_DIST = {32: "dist32", 64: "dist"}

MACHINE_NAMES = {0x014C: "x86 (32-bit)", 0x8664: "x64 (64-bit)", 0xAA64: "ARM64"}


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="打包教室小喇叭 exe", add_help=True
    )
    parser.add_argument("--arch", choices=["32", "64"], default="64",
                        help="目标位数（默认 64）")
    parser.add_argument("--python", default="",
                        help="用哪个 Python 解释器打包（默认按 --arch 猜）")
    parser.add_argument("--dist", default="", help="输出目录")
    parser.add_argument("--onedir", action="store_true", help="打成目录版而非单文件")
    parser.add_argument("--name", default="ClassSpeaker", help="exe 名称")
    args, unknown = parser.parse_known_args(argv)
    if "dir" in unknown:          # 兼容旧写法：python build_exe.py dir
        args.onedir = True
    return args


def interpreter(arch, explicit):
    if explicit:
        return explicit
    candidate = DEFAULT_PYTHON.get(int(arch), sys.executable)
    return candidate if os.path.isfile(candidate) else sys.executable


def python_arch(python):
    code = "import struct;print(struct.calcsize('P')*8)"
    try:
        out = subprocess.check_output([python, "-c", code], text=True).strip()
        return int(out)
    except Exception:
        return 0


def has_deps(python):
    code = "import PyQt5, PyInstaller; print('ok')"
    try:
        subprocess.check_output([python, "-c", code], text=True,
                                stderr=subprocess.STDOUT)
        return True
    except Exception:
        return False


def pe_machine(path):
    try:
        with open(path, "rb") as fh:
            if fh.read(2) != b"MZ":
                return 0
            fh.seek(0x3C)
            offset = struct.unpack("<I", fh.read(4))[0]
            fh.seek(offset)
            if fh.read(4) != b"PE\0\0":
                return 0
            return struct.unpack("<H", fh.read(2))[0]
    except Exception:
        return 0


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    python = interpreter(args.arch, args.python)
    dist = os.path.join(ROOT, args.dist or DEFAULT_DIST.get(int(args.arch), "dist"))
    work = os.path.join(ROOT, "build" + ("" if args.arch == "64" else args.arch))
    icon = os.path.join(ROOT, "classspeaker", "assets", "app.ico")

    print("解释器 : {}".format(python))
    if not os.path.isfile(python):
        print("[错误] 找不到解释器，请用 --python 指定。")
        return 1
    actual = python_arch(python)
    print("位数   : {} 位（目标 {} 位）".format(actual, args.arch))
    if actual and actual != int(args.arch):
        print("[警告] 解释器位数与 --arch 不一致，将以解释器为准。")
    if not has_deps(python):
        print("[错误] 这个解释器缺少依赖，请先执行：")
        print('       "{}" -m pip install PyQt5 pyinstaller'.format(python))
        return 1

    py_args = [
        python, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onedir" if args.onedir else "--onefile",
        "--windowed",
        "--name", args.name,
        "--distpath", dist,
        "--workpath", work,
        "--specpath", work,
        "--hidden-import", "winsound",
        "--hidden-import", "winreg",
        # 源路径必须写绝对路径：PyInstaller 按 spec 文件所在目录解析相对路径
        "--add-data", "{}{}classspeaker/web".format(
            os.path.join(ROOT, "classspeaker", "web"), SEP),
        "--add-data", "{}{}classspeaker/assets".format(
            os.path.join(ROOT, "classspeaker", "assets"), SEP),
    ]
    if os.path.isfile(icon):
        py_args += ["--icon", icon]
    else:
        print("[提示] 没有 app.ico，本次用默认图标；可先跑 python tools\\make_icon.py")
    py_args.append(os.path.join(ROOT, "run.py"))

    print("开始打包（{}）…".format("目录版" if args.onedir else "单文件版"))
    result = subprocess.call(py_args, cwd=ROOT)
    if result != 0:
        print("打包失败，PyInstaller 返回 {}".format(result))
        return result

    if args.onedir:
        target = os.path.join(dist, args.name, "{}.exe".format(args.name))
    else:
        target = os.path.join(dist, "{}.exe".format(args.name))
    if not os.path.isfile(target):
        print("打包结束，但没有找到输出文件 {}".format(target))
        return 1

    machine = pe_machine(target)
    print("\n完成：{}".format(target))
    print("      大小 {:.1f} MB，位数 {}".format(
        os.path.getsize(target) / 1024.0 / 1024.0,
        MACHINE_NAMES.get(machine, "未知(0x%X)" % machine),
    ))
    print("      把 exe 拷到教室电脑任意目录双击即可，设置窗口首次运行会自动弹出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

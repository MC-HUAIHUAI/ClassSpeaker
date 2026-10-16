# -*- coding: utf-8 -*-
"""通用小工具：日志、JSON 读写、网络信息。"""
import datetime
import json
import os
import socket
import threading

from . import paths

_IO_LOCK = threading.Lock()
_LOG_LOCK = threading.Lock()


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {} if default is None else default


def write_json_atomic(path, data):
    """先写临时文件再替换，避免断电/崩溃写坏配置。"""
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception:
        pass
    tmp = path + ".tmp"
    with _IO_LOCK:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)


class Logger(object):
    """极简日志：控制台 + 文件，任何异常都不向上抛。"""

    def __init__(self, path=None, echo=True):
        self.path = path or paths.LOG_PATH
        self.echo = echo

    def _write(self, level, message):
        line = "[{}] [{}] {}".format(now_str(), level, message)
        if self.echo:
            try:
                print(line)
            except Exception:
                pass
        try:
            with _LOG_LOCK:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        except Exception:
            pass

    def info(self, message):
        self._write("INFO", message)

    def warn(self, message):
        self._write("WARN", message)

    def error(self, message):
        self._write("ERROR", message)

    def exception(self, message):
        import traceback

        self._write("ERROR", "{}\n{}".format(message, traceback.format_exc()))


LOG = Logger()


def hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "classroom"


def primary_lan_ip():
    """取默认出口网卡的 IPv4；校园局域网下即为本机内网地址。"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.6)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        pass
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        for info in infos:
            addr = info[4][0]
            if addr and not addr.startswith("127."):
                return addr
    except Exception:
        pass
    return "127.0.0.1"


def all_lan_ips():
    """尽量列出本机所有可用的 IPv4 地址（无需第三方库）。"""
    found = []
    primary = primary_lan_ip()
    if primary:
        found.append(primary)
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        for info in infos:
            addr = info[4][0]
            if addr and not addr.startswith("127.") and addr not in found:
                found.append(addr)
    except Exception:
        pass
    return found


def port_is_free(port, bind="0.0.0.0"):
    """只用普通 bind 探测，不能带 SO_REUSEADDR。

    Windows 上 SO_REUSEADDR 允许"抢绑"别人已占用的端口，
    带上它会把被占用的端口误判为空闲。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((bind, int(port)))
        return True
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def find_free_port(start=8080, end=8200, bind="0.0.0.0"):
    for port in range(int(start), int(end) + 1):
        if port_is_free(port, bind):
            return port
    return None


def human_duration(seconds):
    seconds = int(max(0, seconds))
    if seconds < 60:
        return "{} 秒".format(seconds)
    if seconds < 3600:
        return "{} 分 {} 秒".format(seconds // 60, seconds % 60)
    return "{} 小时 {} 分".format(seconds // 3600, (seconds % 3600) // 60)

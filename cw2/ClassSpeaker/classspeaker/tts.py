# -*- coding: utf-8 -*-
"""离线语音播报：把老师发的消息念出来（中文 / 英文自动切换）。

为什么用 System.Speech 而不是 win32com：
  Class Widgets 自带的 Python 只有 `win32`（没有 `win32com`），系统 Python 也没有
  pywin32，所以 COM 后端不可用；而 .NET 的 System.Speech 每台 Windows 都有，
  通过 powershell.exe 调用即可，**完全离线、零第三方依赖**。

两个关键细节：
  * 脚本用 `-EncodedCommand`（UTF-16LE base64）传给 powershell，中文不会乱码；
  * 一段文字里中英文混排时，按字符脚本切成多段，各自 SelectVoice 后朗读，
    所以"第 3 排的同学请打开 Unit 5"这种句子两个语言都能念对。

停止：朗读跑在独立子进程里，点「确认收到」时直接 kill，响应是即时的。
"""
import base64
import re
import subprocess
import sys
import threading

CREATE_NO_WINDOW = 0x08000000

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
                     r"\u3040-\u30ff\uac00-\ud7af]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_SENTENCE_END = "。！？!?；;…\n\r"

MAX_CHUNK = 60          # 单段最长字符数（也是"确认收到"后最多再念多久的上限）
PUNCT_BREAK = " ，,、/：:）)。"


# ---------------------------------------------------------------- 文本分析
def voice_language(hint):
    """从语种/描述里判断 zh / en（判断不出来返回空串）。"""
    text = (hint or "").strip().lower()
    if not text:
        return ""
    if text.startswith("zh") or "chinese" in text or "中文" in text \
            or "simplified" in text:
        return "zh"
    if text.startswith("en") or "english" in text:
        return "en"
    return ""


def _sentences(text):
    buf = []
    for ch in text:
        buf.append(ch)
        if ch in _SENTENCE_END:
            yield "".join(buf)
            buf = []
    if buf:
        yield "".join(buf)


def _script_runs(piece):
    """把一句拆成 [(lang, 连续文本)]，中文/英文交替。"""
    runs = []
    cur_lang = None
    cur = []
    for ch in piece:
        if _CJK_RE.match(ch):
            lang = "zh"
        elif _LATIN_RE.match(ch):
            lang = "en"
        else:
            lang = None          # 数字/标点/空格跟随当前段
        if lang is None:
            cur.append(ch)
            continue
        if cur_lang is None:
            cur_lang = lang
            cur.append(ch)
        elif lang == cur_lang:
            cur.append(ch)
        else:
            runs.append((cur_lang, "".join(cur)))
            cur_lang, cur = lang, [ch]
    if cur:
        runs.append((cur_lang or "zh", "".join(cur)))
    return runs


def _chunk(text, max_len):
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text]
    parts = []
    while len(text) > max_len:
        cut = max_len
        for index in range(max_len, max(0, max_len - 20), -1):
            if text[index - 1] in PUNCT_BREAK:
                cut = index
                break
        parts.append(text[:cut])
        text = text[cut:]
    if text.strip():
        parts.append(text)
    return parts


def split_by_language(text, max_len=MAX_CHUNK):
    """把整段文字切成 [(lang, text)]，每段不超过 max_len，供逐段选择语音朗读。"""
    segments = []
    for piece in _sentences(text or ""):
        for lang, run in _script_runs(piece):
            for part in _chunk(run, max_len):
                # 只有合并后仍不超长才合并，保证单段上限
                if (segments and segments[-1][0] == lang
                        and len(segments[-1][1]) + len(part) <= max_len):
                    segments[-1] = (lang, segments[-1][1] + part)
                else:
                    segments.append((lang, part))
    return [(lang, chunk.strip()) for lang, chunk in segments if chunk.strip()]


# ---------------------------------------------------------------- 引擎
def _escape_ps(text):
    return (text or "").replace("'", "''")


def _run_powershell(script, timeout=25):
    """同步执行一段 PowerShell（UTF-16LE base64 传入），返回 stdout 文本。"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW,
        timeout=timeout,
    )
    return result.stdout.decode("utf-8", "replace")


class TTSEngine(object):
    """语音引擎。spawner / voices_provider 可注入，方便测试时不发声。"""

    def __init__(self, spawner=None, voices_provider=None):
        self._lock = threading.RLock()
        self._proc = None
        self._voices_cache = None
        self._spawner = spawner or self._default_spawner
        self._voices_provider = voices_provider or self._default_voices

    @staticmethod
    def supported():
        return sys.platform.startswith("win")

    # ---------- 语音列表 ----------
    def voices(self, refresh=False):
        """返回 [(名称, 语种)]，例如 [("Microsoft Huihui Desktop", "zh-CN")]。"""
        with self._lock:
            if self._voices_cache is not None and not refresh:
                return list(self._voices_cache)
        try:
            found = list(self._voices_provider() or [])
        except Exception:
            found = []
        with self._lock:
            self._voices_cache = found
        return list(found)

    def pick_voice(self, lang, preferred=""):
        """按语言挑一个语音；preferred 命中就优先用。"""
        voices = self.voices()
        if preferred:
            for name, _culture in voices:
                if name == preferred:
                    return name
        for name, culture in voices:
            if voice_language(culture) == lang:
                return name
        for name, _culture in voices:
            if voice_language(name) == lang:
                return name
        return ""

    # ---------- 组装脚本（纯函数，便于测试）----------
    def build_script(self, segments, rate=0, volume=100,
                     voice_zh="", voice_en=""):
        lines = [
            "Add-Type -AssemblyName System.Speech",
            "$ErrorActionPreference = 'SilentlyContinue'",
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
            "$s.Rate = {}".format(max(-10, min(10, int(rate)))),
            "$s.Volume = {}".format(max(0, min(100, int(volume)))),
        ]
        for lang, text in segments:
            preferred = voice_zh if lang == "zh" else voice_en
            name = self.pick_voice(lang, preferred)
            if name:
                lines.append("try {{ $s.SelectVoice('{}') }} catch {{}}".format(
                    _escape_ps(name)))
            lines.append("$s.Speak('{}')".format(_escape_ps(text)))
        lines.append("$s.Dispose()")
        return "\n".join(lines)

    # ---------- 朗读 ----------
    def speak(self, text, rate=0, volume=100, voice_zh="", voice_en=""):
        """开始朗读（非阻塞）。返回是否真的开始。"""
        if not self.supported():
            return False
        segments = split_by_language(text)
        if not segments:
            return False
        script = self.build_script(segments, rate, volume, voice_zh, voice_en)
        self.stop()
        try:
            proc = self._spawner(script)
        except Exception:
            return False
        if proc is None:
            return False
        with self._lock:
            self._proc = proc
        threading.Thread(target=self._reap, args=(proc,), daemon=True).start()
        return True

    def stop(self):
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
        except Exception:
            pass

    @property
    def busy(self):
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    # ---------- 默认后端 ----------
    def _reap(self, proc):
        try:
            proc.wait()
        except Exception:
            pass
        finally:
            with self._lock:
                if self._proc is proc:
                    self._proc = None

    @staticmethod
    def _default_spawner(script):
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW,
        )

    @staticmethod
    def _default_voices():
        script = (
            "[Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
            "Add-Type -AssemblyName System.Speech\n"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
            "$s.GetInstalledVoices() | ForEach-Object {\n"
            "  if ($_.Enabled) {\n"
            "    Write-Output ($_.VoiceInfo.Name + '|' + $_.VoiceInfo.Culture.Name)\n"
            "  }\n"
            "}\n"
            "$s.Dispose()\n"
        )
        output = _run_powershell(script)
        voices = []
        for line in output.splitlines():
            line = line.strip()
            if "|" not in line:
                continue
            name, culture = line.rsplit("|", 1)
            if name.strip():
                voices.append((name.strip(), culture.strip()))
        return voices


# 全局单例 + 便捷函数
engine = TTSEngine()


def voices(refresh=False):
    return engine.voices(refresh=refresh)


def speak(text, rate=0, volume=100, voice_zh="", voice_en=""):
    return engine.speak(text, rate=rate, volume=volume,
                        voice_zh=voice_zh, voice_en=voice_en)


def stop():
    engine.stop()


def preview(text=None, rate=0, volume=100, voice_zh="", voice_en=""):
    """设置界面「试听」用：给一段中英文示例。"""
    sample = text or ("语音播报已开启。This is an English sentence for testing. "
                      "中英文混排也能正常朗读。")
    return speak(sample, rate=rate, volume=volume,
                 voice_zh=voice_zh, voice_en=voice_en)

# -*- coding: utf-8 -*-
"""语音播报（离线 TTS）测试：不发声、不需要语音包。

    python tools/tts_test.py

覆盖：中英文切分、语音挑选、PowerShell 脚本生成、进程启停。
"""
import os
import sys
import threading

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from classspeaker import tts  # noqa: E402

PASSED = []
FAILED = []

FAKE_VOICES = [
    ("Microsoft Huihui Desktop", "zh-CN"),
    ("Microsoft Zira Desktop", "en-US"),
    ("Microsoft David Desktop", "en-US"),
]


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  [PASS] {}{}".format(name, ("  " + detail) if detail else ""))
    else:
        FAILED.append(name)
        print("  [FAIL] {}{}".format(name, ("  " + detail) if detail else ""))


class FakeProc(object):
    """假的子进程：记录 kill，可手动结束。"""

    def __init__(self):
        self.killed = False
        self.returncode = None
        self._done = threading.Event()

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self._done.wait(0.5 if timeout is None else timeout)
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        self._done.set()

    def finish(self, code=0):
        self.returncode = code
        self._done.set()


def make_engine(spawned=None, voices=None):
    spawned = spawned if spawned is not None else []

    def spawner(script):
        proc = FakeProc()
        spawned.append((script, proc))
        return proc

    return tts.TTSEngine(
        spawner=spawner,
        voices_provider=lambda: list(voices or FAKE_VOICES),
    ), spawned


def main():
    print("\n== 语言判定 ==")
    check("zh-CN → 中文", tts.voice_language("zh-CN") == "zh")
    check("en-US → 英文", tts.voice_language("en-US") == "en")
    check("描述里含 Chinese → 中文",
          tts.voice_language("Microsoft Huihui Desktop - Chinese (Simplified)") == "zh")
    check("空值 → 未知", tts.voice_language("") == "")

    print("\n== 中英文切分 ==")
    seg = tts.split_by_language("第三排的同学请到讲台领取试卷。")
    check("纯中文 → 一段", len(seg) == 1 and seg[0][0] == "zh", str(seg))

    seg = tts.split_by_language("Hello everyone.")
    check("纯英文 → 一段", len(seg) == 1 and seg[0][0] == "en", str(seg))

    seg = tts.split_by_language("请打开 Unit 5 的练习册。")
    check("中英混排 → 三段 zh/en/zh",
          [item[0] for item in seg] == ["zh", "en", "zh"], str(seg))
    check("英文段保留了 Unit 5",
          any("Unit 5" in chunk for lang, chunk in seg if lang == "en"), str(seg))

    seg = tts.split_by_language("Hello everyone, 今天作业是第十页。")
    check("英中混排 → en/zh",
          [item[0] for item in seg] == ["en", "zh"], str(seg))

    check("空文本 → 空列表", tts.split_by_language("   ") == [])
    check("None → 空列表", tts.split_by_language(None) == [])

    long_text = "请同学们打开课本。" * 12
    seg = tts.split_by_language(long_text)
    check("长文本会被切段（单段不超过上限）",
          len(seg) > 1 and all(len(chunk) <= tts.MAX_CHUNK for _l, chunk in seg),
          "{} 段，最长 {} 字".format(
              len(seg), max(len(c) for _l, c in seg)))
    check("切段后内容不丢字",
          "".join(chunk for _l, chunk in seg).replace(" ", "")
          == long_text.replace(" ", ""))

    print("\n== 语音挑选 ==")
    engine, _spawned = make_engine()
    check("自动挑中文语音",
          engine.pick_voice("zh") == "Microsoft Huihui Desktop",
          engine.pick_voice("zh"))
    check("自动挑英文语音",
          engine.pick_voice("en") == "Microsoft Zira Desktop",
          engine.pick_voice("en"))
    check("优先用用户指定的语音",
          engine.pick_voice("en", "Microsoft David Desktop") == "Microsoft David Desktop")
    check("指定的语音不存在时回退到自动",
          engine.pick_voice("zh", "不存在的语音") == "Microsoft Huihui Desktop")
    check("没有对应语言的语音时返回空",
          tts.TTSEngine(voices_provider=lambda: [("X", "de-DE")]).pick_voice("zh") == "")

    print("\n== 脚本生成 ==")
    script = engine.build_script(
        [("zh", "上课了"), ("en", "Lesson one")], rate=3, volume=70)
    check("设置了语速", "$s.Rate = 3" in script)
    check("设置了音量", "$s.Volume = 70" in script)
    check("中文段用中文语音",
          "SelectVoice('Microsoft Huihui Desktop')" in script)
    check("英文段用英文语音",
          "SelectVoice('Microsoft Zira Desktop')" in script)
    check("两段都调用了 Speak",
          script.count("$s.Speak(") == 2, str(script.count("$s.Speak(")))
    check("最后释放语音对象", "$s.Dispose()" in script)

    check("单引号被转义（防止脚本注入/语法错误）",
          "it''s" in engine.build_script([("en", "it's fine")]))
    check("语速被限制在 -10~10",
          "$s.Rate = -10" in engine.build_script([("en", "x")], rate=-99))
    check("音量被限制在 0~100",
          "$s.Volume = 100" in engine.build_script([("en", "x")], volume=999))

    print("\n== 朗读与停止 ==")
    engine, spawned = make_engine()
    ok = engine.speak("上课了")
    check("speak 返回 True", ok is True)
    check("确实启动了一个进程", len(spawned) == 1)
    check("脚本里带要念的文字", "上课了" in spawned[0][0])
    check("朗读中 busy 为 True", engine.busy is True)

    spawned[0][1].finish()
    threading.Event().wait(0.2)
    check("进程结束后 busy 变 False", engine.busy is False)

    engine.speak("这是一段会被打断的朗读")
    engine.speak("第二段要顶掉它")
    check("再次 speak 会 kill 掉还在念的上一条",
          spawned[-2][1].killed is True)
    check("新的朗读在跑",
          engine.busy is True and spawned[-1][1].killed is False)

    engine.stop()
    check("stop 后 busy 为 False", engine.busy is False)
    check("stop 会 kill 子进程", spawned[-1][1].killed is True)

    engine2, spawned2 = make_engine()
    check("空文本不会启动进程",
          engine2.speak("   ") is False and not spawned2)

    print("\n== 试听 ==")
    engine3, spawned3 = make_engine()
    original = tts.engine
    tts.engine = engine3
    try:
        ok = tts.preview()
    finally:
        tts.engine = original
    check("preview 能启动朗读", ok is True and len(spawned3) == 1)
    check("试听内容是中英混排", "English" in spawned3[0][0])

    print("\n== 平台与降级 ==")
    check("Windows 上 supported() 为真", tts.TTSEngine.supported() is True)
    check("没有语音时不会崩",
          tts.TTSEngine(spawner=lambda s: FakeProc(),
                        voices_provider=lambda: []).speak("测试") is True)

    print("\n================ 结果 ================")
    print("通过 {} 项，失败 {} 项".format(len(PASSED), len(FAILED)))
    if FAILED:
        for name in FAILED:
            print(" - 失败：{}".format(name))
        return 1
    print("全部通过 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())

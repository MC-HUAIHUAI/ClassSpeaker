# -*- coding: utf-8 -*-
"""生成自带的提示音 assets/notify.wav（无需任何第三方库）。

    python tools/make_sound.py

默认声音是"两声清脆提示音"，出厂关闭（在设置里勾选"消息弹出时播放提示音"即可启用）。
"""
import array
import math
import os
import sys
import wave

SAMPLE_RATE = 44100
AMPLITUDE = 0.55

NOTES = [
    # (起始秒, 时长秒, 基频Hz)
    (0.00, 0.24, 880.0),
    (0.26, 0.42, 1174.7),
]


def envelope(t, duration):
    attack = 0.012
    if t < attack:
        return t / attack
    release = max(0.05, duration - attack)
    return math.exp(-4.2 * (t - attack) / release)


def build_samples():
    total = max(start + dur for start, dur, _freq in NOTES) + 0.12
    frames = int(total * SAMPLE_RATE)
    samples = array.array("h", [0] * frames)
    for start, duration, freq in NOTES:
        begin = int(start * SAMPLE_RATE)
        count = int(duration * SAMPLE_RATE)
        for index in range(count):
            t = index / float(SAMPLE_RATE)
            value = math.sin(2 * math.pi * freq * t)
            value += 0.28 * math.sin(2 * math.pi * freq * 2.0 * t)
            value *= envelope(t, duration)
            position = begin + index
            if position >= frames:
                break
            mixed = samples[position] + int(value * AMPLITUDE * 32767)
            samples[position] = max(-32768, min(32767, mixed))
    # 结尾淡出，避免爆音
    fade = int(0.03 * SAMPLE_RATE)
    for index in range(max(0, frames - fade), frames):
        ratio = (frames - index) / float(fade)
        samples[index] = int(samples[index] * ratio)
    return samples


def write_wav(path, samples):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    handle = wave.open(path, "wb")
    try:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(samples.tobytes())
    finally:
        handle.close()


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = os.path.join(root, "classspeaker", "assets", "notify.wav")
    write_wav(target, build_samples())
    print("已生成提示音：{}（{} 字节）".format(target, os.path.getsize(target)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

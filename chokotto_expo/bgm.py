# 15秒の明るいBGMを合成して bgm.wav に書き出す
import sys, wave
import numpy as np

SR = 44100
DUR = 15.0
BPM = 120
BEAT = 60 / BPM          # 1拍 = 0.5秒
N = int(SR * DUR)
out = np.zeros(N)

def note_freq(n):        # MIDIノート番号 → 周波数(Hz)
    return 440.0 * 2 ** ((n - 69) / 12)

def add(sig, start):
    i = int(start * SR)
    j = min(N, i + len(sig))
    if i < N:
        out[i:j] += sig[: j - i]

def tone(freq, length, kind="square", vol=0.2, attack=0.005, release=0.08):
    t = np.arange(int(length * SR)) / SR
    if kind == "square":
        w = np.sign(np.sin(2 * np.pi * freq * t)) * 0.6 + np.sin(2 * np.pi * freq * t) * 0.4
    elif kind == "tri":
        w = 2 / np.pi * np.arcsin(np.sin(2 * np.pi * freq * t))
    else:
        w = np.sin(2 * np.pi * freq * t)
    env = np.ones_like(t)
    a = int(attack * SR); r = int(release * SR)
    env[:a] = np.linspace(0, 1, a)
    if r < len(env):
        env[-r:] = np.linspace(1, 0, r)
    env *= np.exp(-t * 2.5)      # 少しずつ減衰させてポップな音に
    return w * env * vol

def kick():
    t = np.arange(int(0.25 * SR)) / SR
    f = 120 * np.exp(-t * 25) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * 0.9

def hat():
    t = np.arange(int(0.05 * SR)) / SR
    rng = np.random.default_rng(0)
    n = rng.uniform(-1, 1, len(t))
    n = np.diff(n, prepend=0)      # 高音寄りのノイズ
    return n * np.exp(-t * 80) * 0.18

def clap():
    t = np.arange(int(0.15 * SR)) / SR
    rng = np.random.default_rng(1)
    return rng.uniform(-1, 1, len(t)) * np.exp(-t * 30) * 0.25

# コード進行: C - G - Am - F（1小節=4拍=2秒）
chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
bass   = [36, 43, 45, 41]
# メロディ（拍単位: (開始拍, ノート, 長さ拍)）を2小節分 × パターン
melody_a = [(0,72,.5),(.5,74,.5),(1,76,1),(2,79,.5),(2.5,76,.5),(3,74,1),
            (4,74,.5),(4.5,76,.5),(5,79,1),(6,81,.5),(6.5,79,.5),(7,76,1)]
melody_b = [(0,76,.5),(.5,77,.5),(1,81,1),(2,79,.5),(2.5,77,.5),(3,76,1),
            (4,74,.5),(4.5,76,.5),(5,77,.5),(5.5,79,.5),(6,84,2)]

bars = int(DUR / (BEAT * 4)) + 1
for b in range(bars):
    t0 = b * BEAT * 4
    last = b >= 7                       # 最後の小節(14秒〜)はジャーンで締める
    ch = chords[b % 4]
    if last:
        for n in [60, 64, 67, 72]:
            add(tone(note_freq(n), 1.0, "tri", 0.12, release=0.6), t0)
        add(tone(note_freq(36), 1.0, "sine", 0.35, release=0.6), t0)
        add(kick(), t0)
        continue
    for beat in range(4):
        t = t0 + beat * BEAT
        if b > 0 or beat >= 2:          # イントロは後半から
            add(kick(), t)
        if beat in (1, 3):
            add(clap(), t)
        for h in (0, 0.5):
            add(hat(), t + h * BEAT)
        # ベース（8分刻み）
        for h in (0, 0.5):
            add(tone(note_freq(bass[b % 4]), BEAT * 0.45, "tri", 0.35), t + h * BEAT)
        # コード（裏拍で刻む）
        for n in ch:
            add(tone(note_freq(n), BEAT * 0.4, "tri", 0.07), t + 0.5 * BEAT)
    # メロディ（1小節目から）
    if b >= 1:
        mel = melody_a if (b - 1) % 4 < 2 else melody_b
        half = 0 if (b - 1) % 2 == 0 else 4
        for st, n, ln in mel:
            if half <= st < half + 4:
                add(tone(note_freq(n), ln * BEAT * 0.9, "square", 0.09), t0 + (st - half) * BEAT)

# 最後0.6秒をフェードアウト、音量を正規化
fade = int(0.6 * SR)
out[-fade:] *= np.linspace(1, 0, fade)
out = out / np.max(np.abs(out)) * 0.85
pcm = (out * 32767).astype(np.int16)
stereo = np.column_stack([pcm, pcm]).ravel()
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(stereo.tobytes())
print("BGM ok")

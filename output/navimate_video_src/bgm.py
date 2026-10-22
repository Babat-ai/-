# BGM自動生成：軽やかなローファイ・ポップ（エレピ＋ベース＋ドラム＋パッド）
import json, wave
import numpy as np

TL = json.load(open("voice/timeline.json"))
SC = {s["id"]: s for s in TL["scenes"]}
DUR = TL["total"] + 0.5
SR = 44100
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N)
BPM = 96; beat = 60 / BPM; bar = beat * 4
rng = np.random.default_rng(7)

def f(m): return 440 * 2 ** ((m - 69) / 12)
def add(sig, t, pan=0.5, gain=1.0):
    i = int(t * SR)
    if i >= N or i < 0: return
    j = min(N, i + len(sig)); s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt(1 - pan); R[i:j] += s * np.sqrt(pan)
def env(n, a, d):
    t = np.arange(n) / SR; e = np.exp(-t / d); ai = int(a * SR)
    if ai > 0: e[:ai] *= np.linspace(0, 1, ai)
    return e

# 区間（ブレイク＝チャプター画面）
def span(i): return SC[i]["start"], SC[i]["start"] + SC[i]["dur"]
brk = [span("ch1"), span("ch2")]
end0 = SC["end"]["start"]
def in_break(t): return any(a - 0.3 <= t < b - 0.2 for a, b in brk)

# コード進行（キー：C）
A = [[53, 64, 67, 69, 72], [55, 65, 69, 71, 74], [52, 62, 67, 71, 74], [57, 64, 67, 71, 72]]  # Fmaj9 G6/9 Em7 Am7
B = [[50, 60, 65, 69, 72], [55, 65, 69, 71, 76], [48, 59, 64, 67, 71], [57, 60, 64, 67, 71]]  # Dm9 G13 Cmaj7 Am9
def chord(t):
    b = int(t / bar)
    prog = A if t < SC["ch1"]["start"] or t >= end0 else (B if (b // 8) % 2 == 0 else A)
    return prog[b % 4]

def epiano(m, n, vel):
    t = np.arange(n) / SR; fr = f(m)
    mod = np.sin(2 * np.pi * fr * 14 * t) * 0.9 * np.exp(-t / 0.08)
    s = np.sin(2 * np.pi * fr * t + mod) + 0.25 * np.sin(2 * np.pi * fr * 2 * t) * np.exp(-t / 0.4)
    s *= 1 + 0.05 * np.sin(2 * np.pi * 5 * t)  # トレモロ
    return s * env(n, 0.004, 0.9) * vel

nb = int(DUR / bar) + 1
for b in range(nb):
    t0 = b * bar; ch = chord(t0 + 0.01)
    br = in_break(t0 + 0.01)
    intro = t0 < 6.5
    outro = t0 > TL["total"] - 7
    # パッド
    n = int(bar * SR * 1.1); t = np.arange(n) / SR
    pe = np.minimum(1, t / 0.5) * np.minimum(1, np.maximum(0, (bar * 1.1 - t) / 0.5))
    for k, m in enumerate(ch[1:]):
        s = np.zeros(n)
        for det in (-0.08, 0.08):
            fr = f(m) * 2 ** (det / 12)
            s += np.sin(2 * np.pi * fr * t) + 0.18 * np.sin(4 * np.pi * fr * t)
        add(s * pe, t0, pan=0.25 + 0.17 * k, gain=0.022 if not br else 0.03)
    # エレピのコンピング（シンコペーション）
    if not br:
        for bt, ln, v in ((0, 1.4, 1.0), (1.5, 0.9, 0.7), (2.75, 0.8, 0.8)):
            for k, m in enumerate(ch[1:]):
                add(epiano(m, int(ln * beat * SR + 0.6 * SR), v), t0 + bt * beat + k * 0.008, pan=0.4 + 0.05 * k, gain=0.028 if not intro else 0.02)
    # ベル系アルペジオ
    if not br and not intro and (b % 2 == 1 or t0 >= end0):
        pat = [4, 3, 2, 3, 4, 2, 3, 1]
        for e in range(8):
            if e in (1, 5): continue
            m = ch[pat[e]] + 12; n = int(0.7 * SR); t = np.arange(n) / SR; fr = f(m)
            s = (np.sin(2 * np.pi * fr * t) + 0.3 * np.sin(2 * np.pi * fr * 3.0 * t) * np.exp(-t / 0.05)) * env(n, 0.002, 0.18)
            add(s, t0 + e * beat / 2, pan=0.2 + 0.6 * (e % 2), gain=0.022)
    # ベース
    if not intro and not br:
        root = ch[0] - 12
        for bt, ln, mm in ((0, 1.6, 0), (1.75, 0.5, 0), (2.5, 1.2, 0), (3.5, 0.45, 7)):
            n = int(ln * beat * SR); t = np.arange(n) / SR; fr = f(root + mm)
            s = np.tanh(1.6 * (np.sin(2 * np.pi * fr * t) + 0.25 * np.sin(4 * np.pi * fr * t))) * env(n, 0.006, 0.45)
            s[-200:] *= np.linspace(1, 0, 200)
            add(s, t0 + bt * beat, gain=0.12)
    # ドラム
    drums = (not intro and not br and not outro)
    if drums:
        for bt in (0, 2.5) if b % 2 else (0, 1.75, 2.5):
            n = int(0.4 * SR); t = np.arange(n) / SR
            ph = 2 * np.pi * np.cumsum(48 + 110 * np.exp(-t / 0.025)) / SR
            add(np.sin(ph) * env(n, 0.001, 0.13), t0 + bt * beat, gain=0.30)
        for bt in (1, 3):
            n = int(0.25 * SR); nz = rng.standard_normal(n); nz = np.diff(np.concatenate([[0], nz]))
            t = np.arange(n) / SR
            body = np.sin(2 * np.pi * 190 * t) * env(n, 0.001, 0.05)
            add((nz * 0.6 + body) * env(n, 0.002, 0.07), t0 + bt * beat, pan=0.5, gain=0.075)
        for e in range(8):
            n = int(0.05 * SR); nz = rng.standard_normal(n); nz = np.diff(np.concatenate([[0], nz]))
            sw = 0.035 * beat if e % 2 else 0  # スウィング
            add(nz * env(n, 0.001, 0.012), t0 + e * beat / 2 + sw, pan=0.68, gain=0.03 if e % 2 else 0.018)

# チャプター前のライザー＆インパクト
def whoosh(tt, ln=1.6, gain=0.4):
    n = int(ln * SR); t = np.arange(n) / SR; nz = rng.standard_normal(n)
    out = np.zeros(n); acc = 0.0
    a = np.exp(-2 * np.pi * (200 + 5000 * (t / ln) ** 2) / SR)
    for i in range(n): acc = a[i] * acc + (1 - a[i]) * nz[i]; out[i] = acc
    e = (t / ln) ** 2 * np.minimum(1, (ln - t) / 0.05)
    add(out * e, tt - ln, pan=0.5, gain=gain)
def impact(tt, gain=0.35):
    n = int(1.5 * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(40 + 80 * np.exp(-t / 0.05)) / SR
    add(np.sin(ph) * env(n, 0.001, 0.4), tt, gain=gain)
for cid, nxt in (("ch1", "top"), ("ch2", "check")):
    whoosh(SC[cid]["start"] + 0.35, 1.2, 0.3)
    whoosh(SC[nxt]["start"] - 0.1, 1.8, 0.45); impact(SC[nxt]["start"] - 0.1)
# オープニングのきらめき
for k, m in enumerate([84, 88, 91, 96]):
    n = int(1.6 * SR); t = np.arange(n) / SR
    add(np.sin(2 * np.pi * f(m) * t) * env(n, 0.002, 0.5), 0.3 + k * 0.09, pan=0.3 + 0.13 * k, gain=0.05)
# 最後のコード
n = int(4.0 * SR)
for k, m in enumerate([48, 60, 64, 67, 71, 74]):
    add(epiano(m, n, 1.0), TL["total"] - 5.0 + k * 0.03, pan=0.3 + 0.08 * k, gain=0.04)

# リバーブ
ir_n = int(2.0 * SR); ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.5); ir /= np.sqrt((ir ** 2).sum())
def conv(x):
    m = len(x) + ir_n; F = 1 << int(np.ceil(np.log2(m)))
    return np.fft.irfft(np.fft.rfft(x, F) * np.fft.rfft(ir, F), F)[: len(x)]
L = L + 0.28 * conv(L); R = R + 0.28 * conv(R)
t = np.arange(N) / SR
fade = np.minimum(1, t / 0.8) * np.minimum(1, np.maximum(0, (DUR - t) / 4.0))
L *= fade; R *= fade
pk = max(abs(L).max(), abs(R).max()); L /= pk / 0.89; R /= pk / 0.89
st = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open("bgm.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
print("bgm ok", round(DUR, 1), "sec")

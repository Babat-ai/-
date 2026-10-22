"""
「水曜日のダウンタウン」の説タイトル風オープニングを作るスクリプト
（映像もBGMもプログラムで一から作るので、著作権フリーのオリジナル）

使い方:
  python3 suiyobi/make_setsu_opening.py
  → output/JC卒業エモい説_オープニング.mp4 ができる

説の文章を変えたいときは、下の「設定」の LINES を書きかえるだけでOK。
"""
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ===== 設定 =====
LINES = ["JCメンバーが", "卒業するときは", "エモい説"]  # 1行ずつ「ドン！」と出る
PROPOSER = ""        # 提唱者の名前（例: "提唱者　JC事務局"）。空なら出さない
W, H = 1920, 1080    # 画面サイズ（フルHD）
FPS = 30             # 1秒あたりのコマ数
DURATION = 10.0      # 動画の長さ（秒）
BPM = 120            # BGMのテンポ（1拍 = 0.5秒）
HITS = [2.0, 2.75, 3.5]  # 各行が出るタイミング（秒）。BGMの「ドン」と合わせてある
SR = 44100           # 音のサンプリング周波数

BASE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(BASE, "fonts", "NotoSansJP-Black.otf")
WORK = os.path.join(BASE, "work")
OUTPUT = os.path.join(BASE, "..", "output", "JC卒業エモい説_オープニング.mp4")


# ---------------------------------------------------------------
# 1. 映像パーツ
# ---------------------------------------------------------------
def make_text_image(text, size, fill):
    """白文字＋太い黒フチ＋影の文字画像（背景透明）を作る"""
    font = ImageFont.truetype(FONT, size)
    stroke = size // 10
    l, t, r, b = font.getbbox(text, stroke_width=stroke)
    pad = 40
    img = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    pos = (pad - l, pad - t)

    # 影（ぼかした黒をずらして置く）
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((pos[0] + 12, pos[1] + 12), text, font=font,
                                fill=(0, 0, 0, 200), stroke_width=stroke,
                                stroke_fill=(0, 0, 0, 200))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))

    # 本体（フチつき文字）
    ImageDraw.Draw(img).text(pos, text, font=font, fill=fill,
                             stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return img


def make_background():
    """真ん中が少し明るい、暗い赤黒のグラデーション背景"""
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H / 2) / H) ** 2)
    glow = np.clip(1 - d * 1.6, 0, 1) ** 2
    rgb = np.stack([18 + 70 * glow, 8 + 12 * glow, 10 + 14 * glow], axis=-1)
    return rgb.astype(np.float32)


def ease_out(p):
    """最初は速く、最後はゆっくり止まる動き（0〜1）"""
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def render_frames():
    # 各行の文字画像を最初に1回だけ作っておく（毎コマ作ると遅いので）
    # 最後の行（「〜説」）だけ大きく黄色に、ほかは白
    texts = []
    for i, s in enumerate(LINES):
        last = i == len(LINES) - 1
        texts.append(make_text_image(s, 230 if last else 150,
                                     (255, 226, 0, 255) if last else (255, 255, 255, 255)))
    proposer = make_text_image(PROPOSER, 60, (255, 255, 255, 255)) if PROPOSER else None

    # 縦の並び位置（全体を画面の真ん中にそろえる）
    gap = 10
    total_h = sum(t.height for t in texts) + gap * (len(texts) - 1)
    ys, y = [], (H - total_h) // 2
    for t in texts:
        ys.append(y + t.height // 2)
        y += t.height + gap

    bg = make_background()
    rng = np.random.default_rng(1)
    n = int(DURATION * FPS)

    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         os.path.join(WORK, "video.mp4")],
        stdin=subprocess.PIPE)

    for f in range(n):
        t = f / FPS

        # 背景：ザラザラしたノイズを少し乗せてテレビっぽく
        frame = bg + rng.normal(0, 4, (H, W, 1)).astype(np.float32)
        canvas = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).convert("RGBA")

        # 全体をゆっくりズームさせる（最後の行が出たあと）
        zoom_all = 1 + 0.04 * max(0.0, t - HITS[-1]) / (DURATION - HITS[-1])

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for i, img in enumerate(texts):
            if t < HITS[i]:
                continue
            p = ease_out((t - HITS[i]) / 0.15)          # 0.15秒で着地
            scale = (1.8 - 0.8 * p) * zoom_all           # 大きい→ふつうサイズへ
            w, h = int(img.width * scale), int(img.height * scale)
            piece = img.resize((w, h), Image.LANCZOS)
            if p < 1:
                piece.putalpha(piece.getchannel("A").point(lambda a: int(a * p)))
            cy = H / 2 + (ys[i] - H / 2) * zoom_all
            layer.alpha_composite(piece, (W // 2 - w // 2, int(cy - h / 2)))

        if proposer and t > HITS[-1] + 1.0:
            a = ease_out((t - HITS[-1] - 1.0) / 0.5)
            piece = proposer.copy()
            piece.putalpha(piece.getchannel("A").point(lambda v: int(v * a)))
            layer.alpha_composite(piece, (W - piece.width - 80, H - piece.height - 60))

        # 画面揺れ：「ドン」の直後だけ小刻みに揺らす
        shake = 0.0
        for i, h in enumerate(HITS):
            if 0 <= t - h < 0.3:
                shake = max(shake, (24 if i == len(HITS) - 1 else 12) * (1 - (t - h) / 0.3))
        dx, dy = (rng.uniform(-shake, shake, 2) if shake else (0, 0))
        canvas.paste(layer, (int(dx), int(dy)), layer)

        out = np.asarray(canvas.convert("RGB")).astype(np.float32)

        # 白フラッシュ：「ドン」の瞬間に画面を一瞬明るく
        for i, h in enumerate(HITS):
            if 0 <= t - h < 0.12:
                k = (1 - (t - h) / 0.12) * (0.8 if i == len(HITS) - 1 else 0.45)
                out = out * (1 - k) + 255 * k

        # 最後は暗転
        if t > DURATION - 1.0:
            out *= (DURATION - t) / 1.0

        ffmpeg.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())

    ffmpeg.stdin.close()
    ffmpeg.wait()


# ---------------------------------------------------------------
# 2. BGM（緊張感のあるオリジナル曲）
# ---------------------------------------------------------------
def freq(midi):
    """MIDI番号を周波数（Hz）に変換する（69 = ラ = 440Hz）"""
    return 440 * 2 ** ((midi - 69) / 12)


def place(track, sound, at):
    """track の at 秒の位置に sound を重ねる"""
    i = int(at * SR)
    end = min(len(track), i + len(sound))
    track[i:end] += sound[: end - i]


def saw(f, t):
    """ノコギリ波っぽい音（倍音を重ねて作る）"""
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 8))


def boom(big):
    """「ドン！」：低い音が急降下＋ノイズのアタック"""
    length = 2.5 if big else 1.2
    t = np.arange(int(length * SR)) / SR
    f = 40 + 110 * np.exp(-t * 18)                 # 150Hz → 40Hz に急降下
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (1.8 if big else 3.5))
    noise = np.random.default_rng(3).normal(0, 1, len(t)) * np.exp(-t * 30)
    s = body * 1.0 + noise * 0.35
    if big:                                         # 最後はシンバル風の余韻も
        crash = np.random.default_rng(4).normal(0, 1, len(t))
        crash = np.diff(crash, prepend=0) * np.exp(-t * 1.5) * 0.12
        s += crash
    return s


def make_bgm():
    n = int(DURATION * SR)
    t = np.arange(n) / SR
    track = np.zeros(n)
    beat = 60 / BPM
    rng = np.random.default_rng(2)

    # (a) 不穏な低音のうなり（ラ＋ミ）：じわじわ大きく
    drone = (saw(freq(33), t) + 0.6 * saw(freq(40), t)) * 0.05
    drone *= np.minimum(t / HITS[0], 1)
    track += drone

    # (b) 時計の「チッ、チッ」：最初の「ドン」まで
    tick = rng.normal(0, 1, int(0.015 * SR)) * np.exp(-np.arange(int(0.015 * SR)) / SR * 400)
    for k in range(int(HITS[0] / (beat / 2))):
        place(track, tick * (0.15 + 0.15 * (k % 2 == 0)), k * beat / 2)

    # (c) 「シュワーッ」と盛り上がるライザー
    rise = t < HITS[0]
    sweep_f = 200 + 900 * (t / HITS[0]) ** 2
    riser = np.sin(2 * np.pi * np.cumsum(sweep_f) / SR) * 0.08
    riser += np.diff(rng.normal(0, 1, n), prepend=0) * 0.06
    track += riser * rise * (t / HITS[0]) ** 2

    # (d) 「ドン！」×3（最後が一番大きい）
    for i, h in enumerate(HITS):
        place(track, boom(i == len(HITS) - 1) * (1.0 if i == len(HITS) - 1 else 0.7), h)

    # (e) 最後の「ドン」のあと：刻むベース＋ストリングス風の和音
    start = HITS[-1] + beat
    chords = [[57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 56, 59]]  # Am F G E
    roots = [33, 29, 31, 28]
    k = 0
    while start + k * beat / 2 < DURATION:
        at = start + k * beat / 2
        bar = int((at - start) / (beat * 2)) % 4      # 2拍ごとにコードが変わる
        ln = int(beat / 2 * SR)
        tt = np.arange(ln) / SR
        bass = saw(freq(roots[bar]), tt) * np.exp(-tt * 8) * 0.12
        place(track, bass, at)
        if k % 4 == 0:                                  # 2拍ぶんの和音
            ln2 = int(beat * 2 * SR)
            tt2 = np.arange(ln2) / SR
            pad = sum(saw(freq(m), tt2) for m in chords[bar]) * 0.025
            pad *= np.minimum(tt2 / 0.1, 1) * np.minimum((beat * 2 - tt2) / 0.1, 1)
            place(track, pad, at)
        if k % 2 == 1:                                  # ハイハット
            hat = np.diff(rng.normal(0, 1, int(0.04 * SR)), prepend=0)
            hat *= np.exp(-np.arange(len(hat)) / SR * 80) * 0.08
            place(track, hat, at)
        k += 1

    # 最後はフェードアウトして、音割れしないよう音量をそろえる
    track *= np.clip((DURATION - t) / 1.5, 0, 1)
    track = np.tanh(track * 1.2)          # やわらかく頭打ち（迫力が出る）
    track /= np.max(np.abs(track)) * 1.12

    path = os.path.join(WORK, "bgm.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    return path


# ---------------------------------------------------------------
# 3. 映像と音をくっつける
# ---------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    print("BGMを作曲中...")
    bgm = make_bgm()
    print("映像を描画中...（数十秒かかります）")
    render_frames()
    print("映像と音を合成中...")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(WORK, "video.mp4"),
         "-i", bgm, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
         os.path.abspath(OUTPUT)], check=True)
    print("完成:", os.path.abspath(OUTPUT))

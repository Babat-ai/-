# 画面を「左半分 / 右上 / 右下」に分けて、3枚の写真を順番にフェードインさせる8秒動画を作るスクリプト
import subprocess, sys
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

W, H, FPS, SEC = 1920, 1080, 30, 8.0   # 画面サイズ(16:9)・コマ数/秒・長さ
FADE = 2.0                              # 1枚がフェードインにかける秒数
INTERVAL = 1.5                          # 次の写真が出てくるまでの間隔(秒)
SEAM = 40                               # 写真の境目をぼかす幅(px)
# 写真を置く場所 (x, y, 幅, 高さ): 左半分 → 右上 → 右下
PANELS = [(0, 0, 960, 1080), (960, 0, 960, 540), (960, 540, 960, 540)]

def cover(img, w, h):
    """写真を w×h の枠いっぱいになるよう、はみ出た部分を切り落として拡大・縮小する"""
    r = w / h
    iw, ih = img.size
    if iw / ih > r:
        nw = ih * r; img = img.crop((int((iw - nw) / 2), 0, int((iw + nw) / 2), ih))
    else:
        nh = iw / r; img = img.crop((0, int((ih - nh) / 2), iw, int((ih + nh) / 2)))
    return img.resize((int(w), int(h)), Image.LANCZOS)

def expanded(rect):
    """境目を重ねてぼかすため、隣に写真がある辺だけ SEAM ぶん外へ広げた範囲を返す"""
    x, y, w, h = rect
    x0, y0 = max(x - SEAM, 0), max(y - SEAM, 0)
    x1, y1 = min(x + w + SEAM, W), min(y + h + SEAM, H)
    return x0, y0, x1 - x0, y1 - y0

def seam_mask(ex, ey, ew, eh):
    """画面の端ではない辺だけを、0→1 になめらかに変化させるマスク"""
    def ramp(n, soft_start, soft_end):
        a = np.ones(n, dtype=np.float32)
        r = np.linspace(0, 1, SEAM * 2, dtype=np.float32)
        r = r * r * (3 - 2 * r)                     # なめらかなS字カーブ
        if soft_start: a[:SEAM * 2] = np.minimum(a[:SEAM * 2], r)
        if soft_end:   a[-SEAM * 2:] = np.minimum(a[-SEAM * 2:], r[::-1])
        return a
    ax = ramp(ew, ex > 0, ex + ew < W)
    ay = ramp(eh, ey > 0, ey + eh < H)
    return np.outer(ay, ax)[:, :, None]

def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3

photos = [Image.open(p).convert("RGB") for p in sys.argv[1:4]]
out = sys.argv[4]

panels = []
for ph, rect in zip(photos, PANELS):
    ex, ey, ew, eh = expanded(rect)
    big = cover(ph, ew * 1.1, eh * 1.1)             # ズーム用に1.1倍大きく用意しておく
    big = big.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    panels.append(dict(pos=(ex, ey), size=(ew, eh), big=big, mask=seam_mask(ex, ey, ew, eh)))

# 背景: 3枚を並べた絵を強くぼかして暗くしたもの(黒背景の代わり)
bg = Image.new("RGB", (W, H))
for ph, (x, y, w, h) in zip(photos, PANELS):
    bg.paste(cover(ph, w, h), (x, y))
bg = bg.filter(ImageFilter.GaussianBlur(40))
bg = ImageEnhance.Brightness(bg).enhance(0.35)
bg = np.asarray(bg, dtype=np.float32)

ff = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out,
], stdin=subprocess.PIPE)

for f in range(int(FPS * SEC)):
    t = f / FPS
    frame = bg.copy()
    for i, pn in enumerate(panels):
        start = 0.4 + i * INTERVAL                  # 左 → 右上 → 右下 の順に登場
        p = ease_out((t - start) / FADE)
        if p <= 0:
            continue
        drift = min(max((t - start) / (SEC - start), 0.0), 1.0)
        s = 1.06 - 0.06 * p + 0.03 * drift          # 寄った状態から引いて、そのあとゆっくり寄る
        ew, eh = pn["size"]
        bw, bh = pn["big"].size
        cw, ch = bw / s, bh / s                     # s が大きいほど狭い範囲を切り出す = ズームイン
        box = ((bw - cw) / 2, (bh - ch) / 2, (bw + cw) / 2, (bh + ch) / 2)
        img = np.asarray(pn["big"].resize((ew, eh), Image.BILINEAR, box=box), dtype=np.float32)
        a = pn["mask"] * p
        x, y = pn["pos"]
        region = frame[y:y + eh, x:x + ew]
        frame[y:y + eh, x:x + ew] = region * (1 - a) + img * a
    ff.stdin.write(frame.clip(0, 255).astype(np.uint8).tobytes())

ff.stdin.close()
ff.wait()
print("done:", out)

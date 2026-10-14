# 3枚の写真を左から順番にフェードインさせる3秒動画を作るスクリプト
import subprocess, sys
import numpy as np
from PIL import Image, ImageFilter

W, H, FPS, SEC = 1920, 1080, 30, 3.0   # 画面サイズ(16:9)・コマ数/秒・長さ
SLOT_W, SLOT_H = 580, 326              # 写真1枚の大きさ(16:9)
GAP = 40                                # 写真どうしのすき間
FEATHER = 45                            # 周りをぼかす幅(px)

def load(path):
    """写真を16:9に切り抜き、周りがふわっと消えるマスクを付ける"""
    img = Image.open(path).convert("RGB")
    r = SLOT_W / SLOT_H
    w, h = img.size
    if w / h > r:
        nw = int(h * r); img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / r); img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    img = img.resize((SLOT_W, SLOT_H), Image.LANCZOS)
    # 端から内側に向かって 0→1 になるマスクを作り、さらにぼかして滑らかに
    mask = Image.new("L", (SLOT_W, SLOT_H), 0)
    inner = Image.new("L", (SLOT_W - FEATHER * 2, SLOT_H - FEATHER * 2), 255)
    mask.paste(inner, (FEATHER, FEATHER))
    mask = mask.filter(ImageFilter.GaussianBlur(FEATHER / 2))
    img.putalpha(mask)
    return img

def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3

photos = [load(p) for p in sys.argv[1:4]]
out = sys.argv[4]
total_w = SLOT_W * 3 + GAP * 2
x0 = (W - total_w) // 2
cy = H // 2

ff = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out,
], stdin=subprocess.PIPE)

for f in range(int(FPS * SEC)):
    t = f / FPS
    frame = Image.new("RGB", (W, H), (0, 0, 0))     # 黒背景
    for i, ph in enumerate(photos):
        start = 0.2 + i * 0.55                      # 左から0.55秒ずつずらして登場
        p = ease_out((t - start) / 0.9)             # 0.9秒かけてフェードイン
        if p <= 0:
            continue
        scale = 1.06 - 0.06 * p                     # 少し大きい状態から元のサイズへ
        sw, sh = int(SLOT_W * scale), int(SLOT_H * scale)
        im = ph.resize((sw, sh), Image.BILINEAR)
        a = np.array(im.getchannel("A"), dtype=np.float32) * p
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
        cx = x0 + i * (SLOT_W + GAP) + SLOT_W // 2
        y = cy - sh // 2 + int(20 * (1 - p))        # 少し下から浮き上がる
        frame.paste(im, (cx - sw // 2, y), im)
    ff.stdin.write(frame.tobytes())

ff.stdin.close()
ff.wait()
print("done:", out)

# 15秒の縦型動画のフレームを描画して ffmpeg に流し込む
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

UP = "/root/.claude/uploads/6edb1ecd-2d53-56e3-80e1-5906de9c1bc0/"
W, H, FPS, DUR = 1080, 1920, 30, 15.0
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
BGM, OUT = sys.argv[1], sys.argv[2]

poster = Image.open(UP + "d044493c-image.jpg").convert("RGB")
stamps = [Image.open(UP + f).convert("RGB") for f in [
    "d888d5ac-image.jpg", "391e8e4f-image.jpg", "3837e3d4-image.jpg",
    "d7b5fa58-image.jpg", "ccd53c62-image.jpg", "ea719852-image.jpg"]]
insta = Image.open(UP + "0c6bb48f-image.jpg").convert("RGB")

def font(size):
    return ImageFont.truetype(FONT, size)

# 背景：赤→白→青のグラデーション（スタンプ紹介画像と同じ配色）
def make_bg():
    y = np.linspace(0, 1, H)[:, None]
    red, white, blue = np.array([232, 53, 43]), np.array([245, 245, 248]), np.array([47, 79, 230])
    top = red + (white - red) * np.clip(y / 0.5, 0, 1)
    col = np.where(y < 0.5, top, white + (blue - white) * np.clip((y - 0.5) / 0.5, 0, 1))
    arr = np.repeat(col[:, None, :], W, axis=1).reshape(H, W, 3)
    return Image.fromarray(arr.astype(np.uint8))
BG = make_bg()

def rounded(img, radius=40):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *img.size], radius, fill=255)
    return mask

def paste_card(canvas, img, cx, cy, width, alpha=1.0):
    h = int(img.height * width / img.width)
    card = img.resize((width, h), Image.LANCZOS)
    mask = rounded(card)
    # 影
    sh = Image.new("L", (width + 80, h + 80), 0)
    ImageDraw.Draw(sh).rounded_rectangle([40, 50, width + 40, h + 50], 40, fill=int(110 * alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    canvas.paste((0, 0, 0), (int(cx - width / 2 - 40), int(cy - h / 2 - 40)), sh)
    if alpha < 1:
        mask = mask.point(lambda v: int(v * alpha))
    canvas.paste(card, (int(cx - width / 2), int(cy - h / 2)), mask)

def text(d, xy, s, size, fill="white", stroke=None, sw=0, anchor="mm"):
    d.text(xy, s, font=font(size), fill=fill, anchor=anchor,
           stroke_width=sw, stroke_fill=stroke or fill)

def ease_out(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3

def pop(x):  # ポンっと弾むスケール
    x = min(max(x, 0), 1)
    return 1 + 0.15 * np.sin(x * np.pi) * (1 - x) if x < 1 else 1

def scene_poster(t):
    c = BG.copy(); d = ImageDraw.Draw(c)
    a = ease_out(t / 0.5)
    text(d, (W / 2, 150 - (1 - a) * 80), "堺区で開催！", 96, "white", "#B5121B", 6)
    text(d, (W / 2, 260 - (1 - a) * 80), "万博のスタンプが堺にやってくる", 52, "white", "#B5121B", 3)
    zoom = 1 + 0.05 * (t / 3)
    paste_card(c, poster, W / 2, 1010, int(940 * zoom * (0.85 + 0.15 * a)), a)
    b = ease_out((t - 0.8) / 0.5)
    text(d, (W / 2, 1790 + (1 - b) * 120), "参加費 無料", 84, "white", "#1B2A8A", 6)
    return c

STAMP_DUR = 1.4
def scene_stamps(t):
    c = BG.copy(); d = ImageDraw.Draw(c)
    i = min(int(t / STAMP_DUR), 5)
    lt = t - i * STAMP_DUR
    text(d, (W / 2, 140), "万博パビリオンの", 70, "white", "#B5121B", 5)
    text(d, (W / 2, 240), "スタンプを集めよう！", 84, "white", "#B5121B", 6)
    # 前のスタンプが左へ退場
    if i > 0 and lt < 0.35:
        k = ease_out(lt / 0.35)
        paste_card(c, stamps[i - 1], W / 2 - k * W, 1000, 900, 1 - k)
    # 新しいスタンプが右から登場
    k = ease_out(lt / 0.4)
    s = pop((lt - 0.3) / 0.4)
    paste_card(c, stamps[i], W / 2 + (1 - k) * W, 1000, int(900 * s))
    # 進捗ドット
    for j in range(6):
        x = W / 2 + (j - 2.5) * 70
        r = 20 if j == i else 14
        d.ellipse([x - r, 1790 - r, x + r, 1790 + r],
                  fill="white" if j <= i else None, outline="white", width=4)
    text(d, (W / 2, 1700), f"{i + 1} / 6", 56, "white", "#1B2A8A", 4)
    return c

def scene_end(t):
    c = BG.copy(); d = ImageDraw.Draw(c)
    a = ease_out(t / 0.4)
    text(d, (W / 2, 110), "ちょこっと万博レガシー・", 66, "white", "#B5121B", 5)
    text(d, (W / 2, 200), "ウォーク＆スタンプラリー in 堺区", 58, "white", "#B5121B", 5)
    paste_card(c, insta, W / 2, 790, int(720 * (0.8 + 0.2 * a)), a)
    b = ease_out((t - 0.5) / 0.4)
    y0 = 1400 + (1 - b) * 150
    d.rounded_rectangle([60, y0, W - 60, y0 + 420], 40, fill=(255, 255, 255))
    text(d, (W / 2, y0 + 80), "2026.10.27(火)", 88, "#D7261E", "#D7261E", 2)
    text(d, (W / 2, y0 + 190), "▼", 44, "#1B2A8A")
    text(d, (W / 2, y0 + 290), "11.15(日)", 88, "#1B2A8A", "#1B2A8A", 2)
    text(d, (W / 2, y0 + 380), "参加費 無料・#ちょこっと万博", 46, "#333333")
    return c

def frame(t):
    if t < 3.0:
        img = scene_poster(t)
    elif t < 3.0 + 6 * STAMP_DUR:
        img = scene_stamps(t - 3.0)
    else:
        img = scene_end(t - 3.0 - 6 * STAMP_DUR)
    # 最初と最後のフェード
    f = min(1, t / 0.3, (DUR - t) / 0.4)
    if f < 1:
        img = Image.blend(Image.new("RGB", (W, H), "white"), img, max(f, 0))
    return img

cmd = ["ffmpeg", "-y", "-loglevel", "error",
       "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-i", BGM, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(int(DUR * FPS)):
    p.stdin.write(frame(n / FPS).tobytes())
p.stdin.close(); p.wait()
print("video ok", p.returncode)

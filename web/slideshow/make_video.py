# index.html のスライド情報を読み取り、縦長(スマホ向け)の mp4 動画を作る
# 使い方: python3 make_video.py  →  our-days.mp4 ができる
import re, subprocess, pathlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont

here = pathlib.Path(__file__).parent
W, H = 1080, 1920        # 動画のサイズ(縦長)
FPS = 30                 # 1秒あたりのコマ数
DUR = 4.5                # 1枚あたりの秒数
FADE = 1.0               # 切り替え(クロスフェード)の秒数
ZOOM = 0.06              # ゆっくりズームする量
TEXT = (245, 241, 234)
ACCENT = (143, 211, 255)
BG = (11, 13, 20)

# --- 1) index.html の slides 配列から、写真とキャプションを取り出す ---
html = (here / "index.html").read_text(encoding="utf-8")
slides = []
for line in html.splitlines():
    fields = dict(re.findall(r'(\w+): "([^"]*)"', line))
    if "src" in fields or fields.get("type") == "card":
        slides.append(fields)

# --- 2) フォント ---
def font(name, size, weight=None):
    f = ImageFont.truetype(str(here / "fonts" / name), size)
    if weight:
        f.set_variation_by_axes([weight])
    return f

jp = font("ZenMaruGothic-Medium.ttf", 52)
small = font("ZenMaruGothic-Medium.ttf", 34)
serif = font("CormorantGaramond[wght].ttf", 190, 500)
italic = font("CormorantGaramond-Italic[wght].ttf", 40, 500)
italic_big = font("CormorantGaramond-Italic[wght].ttf", 58, 500)

def text_layer(lines):
    """中央ぞろえの文字を、ぼかした影つきで描いた透明レイヤーを返す"""
    layer = Image.new("RGBA", (W, H))
    shadow = Image.new("RGBA", (W, H))
    for y, txt, f, color in lines:
        for img, fill in ((shadow, (0, 0, 0, 170)), (layer, color + (255,))):
            ImageDraw.Draw(img).text((W / 2, y), txt, font=f, fill=fill, anchor="mm")
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    return Image.alpha_composite(shadow, layer)

# --- 3) スライドごとの「背景」「写真」「文字」を前もって用意 ---
prepared = []
for s in slides:
    if s.get("type") == "card":
        # 小さい画像に色を置いて拡大すると、なめらかなグラデーションになる
        g = Image.new("RGB", (9, 16), BG)
        ImageDraw.Draw(g).ellipse((1, 3, 7, 9), fill=(29, 42, 74))
        bg = g.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BICUBIC)
        txt = text_layer([
            (H * 0.44, s["title"], serif, TEXT),
            (H * 0.44 + 150, s["sub"], italic_big, ACCENT),
            (H * 0.44 + 250, s["note"].replace("← → キー / タップで操作できます", ""), small, (200, 198, 194)),
        ])
        prepared.append((bg, None, txt))
        continue
    photo = Image.open(here / s["src"]).convert("RGB")
    bg = photo.copy()
    bg.thumbnail((W // 4, H // 4))
    bg = bg.resize((W, H)).filter(ImageFilter.GaussianBlur(30))
    bg = Image.blend(Image.new("RGB", (W, H), BG), bg, 0.5)
    box_w, box_h = W - 100, H - 520           # 写真を置く枠(下はキャプション用に空ける)
    scale = min(box_w / photo.width, box_h / photo.height)
    big = photo.resize((round(photo.width * scale * (1 + ZOOM)), round(photo.height * scale * (1 + ZOOM))), Image.LANCZOS)
    txt = text_layer([(H - 300, s["chapter"], italic, ACCENT), (H - 225, s["text"], jp, TEXT)])
    prepared.append((bg, (big, scale, photo.size), txt))

def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def render(i, t):
    """i枚目のスライドの、表示開始から t 秒後の1コマを作る"""
    bg, ph, txt = prepared[i]
    frame = bg.copy()
    if ph:
        big, scale, (pw, ph_) = ph
        z = 1 + ZOOM * ease((t + FADE) / (DUR + FADE))
        w, h = round(pw * scale * z), round(ph_ * scale * z)
        img = big.resize((w, h), Image.BILINEAR)
        frame.paste(img, ((W - w) // 2, 60 + ((H - 520) - h) // 2))
    a = ease((t - 0.3) / 0.8)                 # 文字は少し遅れてふわっと出す
    if a > 0:
        faded = txt.copy()
        faded.putalpha(faded.getchannel("A").point(lambda v: int(v * a)))
        frame.paste(faded, (0, 0), faded)
    return frame

# --- 4) 1コマずつ作って ffmpeg に渡し、mp4 にする ---
out = here / "our-days.mp4"
ff = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-movflags", "+faststart", str(out),
], stdin=subprocess.PIPE)

n = len(prepared)
total = int(n * DUR * FPS)
for k in range(total):
    t = k / FPS
    i = min(int(t // DUR), n - 1)
    lt = t - i * DUR
    frame = render(i, lt)
    if lt > DUR - FADE:
        mix = ease((lt - (DUR - FADE)) / FADE)
        if i + 1 < n:                          # 次のスライドへクロスフェード
            frame = Image.blend(frame, render(i + 1, lt - DUR), mix)
        else:                                  # 最後は黒にフェードアウト
            frame = Image.blend(frame, Image.new("RGB", (W, H), BG), mix)
    if i == 0 and lt < FADE:                   # 最初は黒からフェードイン
        frame = Image.blend(Image.new("RGB", (W, H), BG), frame, ease(lt / FADE))
    ff.stdin.write(frame.tobytes())
    if k % (FPS * 5) == 0:
        print(f"{k / total:4.0%} 作成中…")

ff.stdin.close()
ff.wait()
print(f"完成: {out.name} ({n}枚 / {total / FPS:.0f}秒)")

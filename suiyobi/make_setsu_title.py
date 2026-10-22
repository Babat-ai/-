"""
「水曜日のダウンタウン」の説タイトル画面風の画像を作るスクリプト
（水色の背景・赤い唇・上下の模様をすべてプログラムで描くオリジナル）

使い方:
  python3 suiyobi/make_setsu_title.py
  → output/JC卒業なぜかエモい説.png ができる
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

# ===== 設定 =====
LABEL = "検証"                                  # 上の唇に入る黄色い文字
LINES = ["JCメンバーが卒業すると", "なぜかエモい説"]  # 最後の「説」は赤い箱になる
W, H = 1920, 1080
S = 2                # 2倍の大きさで描いてから縮める（線のギザギザを消すため）

BASE = os.path.dirname(os.path.abspath(__file__))
# 背景画像。None にすると、背景・唇・もようをプログラムで描く
BACKGROUND = os.path.join(BASE, "input", "bg_kensho.webp")
OUTPUT = os.path.join(BASE, "..", "output", "JC卒業なぜかエモい説.png")

# フォント：suiyobi/fonts/ に「ロマン雪」(Roman Yuki) のファイルを置けばそれを使う。
# なければ、形の近い無料フォント Dela Gothic One を横に縮めて代わりに使う
_user_fonts = [f for f in sorted(os.listdir(os.path.join(BASE, "fonts")))
               if ("ロマン" in f or "roman" in f.lower())
               and f.lower().endswith((".ttf", ".otf", ".ttc"))]
if _user_fonts:
    FONT, SQUEEZE = os.path.join(BASE, "fonts", _user_fonts[0]), 1.0
else:
    FONT, SQUEEZE = os.path.join(BASE, "fonts", "DelaGothicOne-Regular.ttf"), 0.82

# 色
CYAN = (128, 240, 240)
CYAN_DARK = (100, 214, 220)    # 背景の薄い唇もよう
RED = (238, 28, 72)
YELLOW = (255, 238, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def P(x, y):
    """1920x1080 の座標を、2倍で描いているキャンバスの座標に直す"""
    return (x * S, y * S)


# ---------------------------------------------------------------
# 背景
# ---------------------------------------------------------------
def draw_bg_pattern(d):
    """背景いっぱいに、薄い「にっこり口」もようを並べる"""
    for row, y in enumerate(range(40, H, 115)):
        shift = 0 if row % 2 == 0 else 85
        for x in range(-60 + shift, W + 100, 170):
            # 上くちびる（山が2つ）と、U字の口
            d.line([P(x - 45, y), P(x - 20, y - 10), P(x, y - 4),
                    P(x + 20, y - 10), P(x + 45, y)], fill=CYAN_DARK, width=4 * S)
            d.arc([P(x - 45, y - 45), P(x + 45, y + 45)], 0, 180,
                  fill=CYAN_DARK, width=4 * S)
            d.line([P(x - 30, y + 14), P(x + 30, y + 14)], fill=CYAN_DARK, width=3 * S)


def paisley(d, cx, cy, r, color, angle):
    """ペイズリー（勾玉みたいな形）を1つ描く"""
    pts = []
    for k in range(0, 300, 10):          # 丸い部分
        a = math.radians(k + angle)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    a = math.radians(angle + 330)        # とがったしっぽ
    pts.append((cx + r * 2.0 * math.cos(a), cy + r * 2.0 * math.sin(a)))
    d.polygon([P(*p) for p in pts], fill=color, outline=BLACK, width=2 * S)
    d.ellipse([P(cx - r * .35, cy - r * .35), P(cx + r * .35, cy + r * .35)],
              fill=WHITE, outline=BLACK, width=S)


def draw_border(canvas, top):
    """上下のカラフルな民族調のもよう帯（下は上を上下反転して配置）"""
    def Y(y):
        return y if top else H - y

    # 別の透明な紙に描いて、帯の高さぶんだけ切り抜いて貼る（はみ出し防止）
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # 太い帯：赤紫の地に、黄色と緑の半円メダル
    d.rectangle([P(0, min(Y(0), Y(62))), P(W, max(Y(0), Y(62)))], fill=(140, 20, 80))
    for i, x in enumerate(range(0, W + 200, 190)):
        c1, c2 = ((255, 220, 40), (30, 120, 200)) if i % 2 == 0 else ((90, 200, 80), (230, 60, 60))
        d.ellipse([P(x - 95, Y(62) - 70), P(x + 95, Y(62) + 70)],
                  fill=c2, outline=BLACK, width=3 * S)
        d.ellipse([P(x - 70, Y(62) - 48), P(x + 70, Y(62) + 48)], fill=c1, outline=BLACK, width=2 * S)
        d.ellipse([P(x - 25, Y(62) - 18), P(x + 25, Y(62) + 18)], fill=(140, 20, 80))
    # メダルのはみ出しを隠すように細い帯を重ねる
    y0, y1 = sorted((Y(62), Y(98)))
    d.rectangle([P(0, y0), P(W, y1)], fill=(20, 140, 170))
    d.line([P(0, Y(62)), P(W, Y(62))], fill=YELLOW, width=5 * S)
    d.line([P(0, Y(98)), P(W, Y(98))], fill=YELLOW, width=5 * S)
    d.line([P(0, Y(101)), P(W, Y(101))], fill=BLACK, width=2 * S)
    colors = [(255, 140, 0), (255, 230, 50), (230, 40, 60), (120, 220, 90)]
    for i, x in enumerate(range(20, W + 40, 52)):
        paisley(d, x, Y(80), 9, colors[i % 4], 200 if top else 20)

    mask = Image.new("L", canvas.size, 0)
    y0, y1 = sorted((Y(0), Y(103)))
    ImageDraw.Draw(mask).rectangle([P(0, y0), P(W, y1)], fill=255)
    canvas.paste(layer, (0, 0), Image.composite(layer.getchannel("A"), mask, mask))


# ---------------------------------------------------------------
# 唇
# ---------------------------------------------------------------
def curve(x0, x1, f, n=80):
    """x0〜x1 の間で、高さ f(u)（u は 0〜1）をたどる点のリスト"""
    return [(x0 + (x1 - x0) * i / n, f(i / n)) for i in range(n + 1)]


def bump(u, p=0.8):
    """両端0・まん中1になるなめらかな山"""
    return math.sin(math.pi * u) ** p


def draw_teeth(d, upper, lower, x0, x1, n):
    """upper と lower の線の間に、白い歯を n 本描く"""
    poly = upper + lower[::-1]
    d.polygon([P(*p) for p in poly], fill=WHITE)
    for k in range(1, n):
        i = round(len(upper) * k / n)
        i = min(i, len(upper) - 1)
        d.line([P(*upper[i]), P(*lower[i])], fill=BLACK, width=5 * S)


def draw_top_mouth(d):
    x0, x1, base = 300, 1620, 130
    lip_top = curve(x0, x1, lambda u: base - 70 * bump(u, .5)
                    + 26 * math.exp(-((u - .5) / .05) ** 2))         # まん中がくぼむ
    lip_bot = curve(x0, x1, lambda u: base + 38 * bump(u))
    teeth_bot = curve(x0, x1, lambda u: base + 118 * bump(u, .9))
    draw_teeth(d, lip_bot, teeth_bot, x0, x1, 14)
    d.polygon([P(*p) for p in lip_top + lip_bot[::-1]], fill=RED)
    d.line([P(*p) for p in lip_bot], fill=BLACK, width=6 * S)
    d.line([P(*p) for p in lip_top + teeth_bot[::-1] + lip_top[:1]], fill=BLACK,
           width=8 * S, joint="curve")


def draw_bottom_mouth(d):
    x0, x1, base = 290, 1630, 862
    teeth_top = curve(x0, x1, lambda u: base + 70 * bump(u, .9))
    lip_top = curve(x0, x1, lambda u: base + 112 * bump(u, .8))
    lip_bot = curve(x0, x1, lambda u: base + 175 * bump(u, .6))
    draw_teeth(d, teeth_top, lip_top, x0, x1, 14)
    d.polygon([P(*p) for p in lip_top + lip_bot[::-1]], fill=RED)
    d.line([P(*p) for p in lip_top], fill=BLACK, width=6 * S)
    d.line([P(*p) for p in teeth_top + lip_bot[::-1] + teeth_top[:1]], fill=BLACK,
           width=8 * S, joint="curve")


# ---------------------------------------------------------------
# 文字
# ---------------------------------------------------------------
def text_image(text, size, fill, stroke=0, squeeze=None, spacing=0):
    """文字を画像にして、横幅を少し縮める（番組のフォントは少し縦長なので）"""
    font = ImageFont.truetype(FONT, size * S)
    chars = []
    for ch in text:
        l, t, r, b = font.getbbox(ch, stroke_width=stroke * S)
        chars.append((ch, font.getlength(ch)))
    width = int(sum(w for _, w in chars) + spacing * S * (len(text) - 1) + stroke * S * 2 + 20)
    height = int(size * S * 1.5)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = stroke * S + 10
    for ch, w in chars:
        d.text((x, height // 2), ch, font=font, fill=fill, anchor="lm",
               stroke_width=stroke * S, stroke_fill=BLACK)
        x += w + spacing * S
    img = img.crop(img.getbbox())
    if squeeze is None:
        squeeze = SQUEEZE
    return img.resize((int(img.width * squeeze), img.height), Image.LANCZOS)


def setsu_box(size):
    """白い「説」が入った赤い四角"""
    ch = text_image("説", int(size * .82), WHITE, squeeze=0.9)
    box = Image.new("RGBA", (int(size * 1.0 * S), int(size * 1.0 * S)), RED + (255,))
    box.alpha_composite(ch, ((box.width - ch.width) // 2, (box.height - ch.height) // 2))
    return box


def draw_texts(canvas, with_label):
    size = 150
    # 黄色い「検証」（上の唇の中）。背景画像にもう入っているときは書かない
    if with_label:
        label = text_image(LABEL, 105, YELLOW, stroke=5, squeeze=0.95, spacing=40)
        canvas.alpha_composite(label, (W * S // 2 - label.width // 2, 70 * S))

    # メインの2行
    pieces = []
    for i, line in enumerate(LINES):
        if i == len(LINES) - 1 and line.endswith("説"):
            body = text_image(line[:-1], size, BLACK)
            box = setsu_box(size)
            gap = 12 * S
            img = Image.new("RGBA", (body.width + gap + box.width, max(body.height, box.height)),
                            (0, 0, 0, 0))
            img.alpha_composite(body, (0, (img.height - body.height) // 2))
            img.alpha_composite(box, (body.width + gap, (img.height - box.height) // 2))
            pieces.append(img)
        else:
            pieces.append(text_image(line, size, BLACK))

    line_gap = 45 * S
    total = sum(p.height for p in pieces) + line_gap * (len(pieces) - 1)
    y = (300 + 840) * S // 2 - total // 2          # 上下の口の間のまん中
    for p in pieces:
        canvas.alpha_composite(p, (W * S // 2 - p.width // 2, y))
        y += p.height + line_gap


if __name__ == "__main__":
    if BACKGROUND:
        canvas = Image.open(BACKGROUND).convert("RGBA").resize((W * S, H * S), Image.LANCZOS)
    else:
        canvas = Image.new("RGBA", (W * S, H * S), CYAN + (255,))
        d = ImageDraw.Draw(canvas)
        draw_bg_pattern(d)
        draw_border(canvas, top=True)
        draw_border(canvas, top=False)
        draw_top_mouth(d)
        draw_bottom_mouth(d)
    draw_texts(canvas, with_label=not BACKGROUND)
    print("フォント:", os.path.basename(FONT))
    out = canvas.resize((W, H), Image.LANCZOS).convert("RGB")
    out.save(os.path.abspath(OUTPUT))
    print("完成:", os.path.abspath(OUTPUT))

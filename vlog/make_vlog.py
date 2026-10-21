"""
縦型Vlogを自動で作るスクリプト

使い方:
  1. vlog/input/ に素材動画を入れる
  2. （任意）vlog/scenes.json に、シーンごとの「使う範囲・速さ・テロップ」を書く
     書かなければ、ファイル名順に自動でカットします
  3. （任意）BGMを使うなら vlog/bgm.mp3 を置く
  4. python3 vlog/make_vlog.py を実行
  5. vlog/output/vlog.mp4 が完成品
"""
import glob
import json
import os
import subprocess

# ===== 設定（ここを変えると仕上がりが変わる） =====
TARGET_SEC = 25      # scenes.json がないときの目標の長さ（秒）
TRIM_HEAD = 0.4      # scenes.json がないとき、各素材の「最初」に切り捨てる秒数
TRIM_TAIL = 0.4      # scenes.json がないとき、各素材の「最後」に切り捨てる秒数
FADE = 0.3           # カット同士を重ねて切り替える秒数（クロスフェード）
WIDTH, HEIGHT = 1080, 1920   # 縦画面（9:16）
FPS = 30

# 色の雰囲気（おしゃれ寄り：少し淡く、少し暖かく、周りを少し暗く）
COLOR_GRADE = (
    "eq=saturation=0.85:contrast=1.05:brightness=0.02,"
    "colorbalance=rs=0.04:bs=-0.04:rm=0.02:bm=-0.02,"
    "vignette=PI/5"
)

# iPhoneのHDR動画を、普通の画面用の色（SDR）に変換するフィルター
HDR_TO_SDR = (
    "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
    "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv"
)

# テロップの見た目
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
TEXT_SIZE = 58
TEXT_Y = "h*0.74"    # 画面の上から74%の位置

BASE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE, "input")
WORK_DIR = os.path.join(BASE, "work")
SCENES = os.path.join(BASE, "scenes.json")
OUTPUT = os.path.join(BASE, "output", "vlog.mp4")


def run(cmd):
    """ffmpegなどのコマンドを実行する（失敗したら止まる）"""
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def probe(path, entry):
    """ffprobeで動画の情報を1つ調べる（例: 長さ、色の種類）"""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entry,
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip().splitlines()[0]


def load_scenes():
    """scenes.json があれば読み込む。なければファイル名順に自動で作る"""
    if os.path.exists(SCENES):
        with open(SCENES, encoding="utf-8") as f:
            return json.load(f)
    exts = ("*.mp4", "*.mov", "*.MP4", "*.MOV", "*.m4v")
    files = sorted(p for e in exts for p in glob.glob(os.path.join(INPUT_DIR, e)))
    if not files:
        return []
    per_clip = (TARGET_SEC + FADE * (len(files) - 1)) / len(files)
    scenes = []
    for path in files:
        dur = float(probe(path, "format=duration"))
        length = max(0.8, min(per_clip, dur - TRIM_HEAD - TRIM_TAIL))
        scenes.append({"file": os.path.basename(path), "start": TRIM_HEAD,
                       "end": TRIM_HEAD + length, "speed": 1.0, "text": ""})
    return scenes


def make_part(i, scene):
    """1シーン分を「切る → 速さを変える → 縦にそろえる → 色 → テロップ」して保存する"""
    src = os.path.join(INPUT_DIR, scene["file"])
    cut = scene["end"] - scene["start"]
    speed = scene.get("speed", 1.0)
    length = cut / speed

    filters = [
        f"setpts=(PTS-STARTPTS)/{speed}",
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase",
        f"crop={WIDTH}:{HEIGHT}",
        "setsar=1",
    ]
    if probe(src, "stream=color_transfer") in ("arib-std-b67", "smpte2084"):
        filters.append(HDR_TO_SDR)
    filters += [f"fps={FPS}", COLOR_GRADE]

    text = scene.get("text", "")
    if text:
        # テロップの文字はファイルに書いて渡す（記号のエスケープを気にしなくて済む）
        text_file = os.path.join(WORK_DIR, f"text{i:02d}.txt")
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(text)
        # 0.4秒かけてふわっと出て、終わり0.4秒でふわっと消える
        alpha = f"if(lt(t,0.4),t/0.4,if(gt(t,{length - 0.4:.3f}),({length:.3f}-t)/0.4,1))"
        filters.append(
            f"drawtext=fontfile={FONT}:textfile={text_file}:fontsize={TEXT_SIZE}:"
            f"fontcolor=white:alpha='{alpha}':x=(w-text_w)/2:y={TEXT_Y}:"
            "shadowcolor=black@0.45:shadowx=0:shadowy=3"
        )
    filters.append("format=yuv420p")

    dst = os.path.join(WORK_DIR, f"part{i:02d}.mp4")
    run(["ffmpeg", "-y", "-ss", str(scene["start"]), "-t", f"{cut:.3f}", "-i", src,
         "-vf", ",".join(filters), "-an", "-c:v", "libx264", "-preset", "fast",
         "-crf", "18", dst])
    print(f"  カット{i + 1}: {scene['file']} {cut:.1f}秒 × {speed}倍速 → {length:.1f}秒「{text}」")
    return dst, length


def main():
    scenes = load_scenes()
    if not scenes:
        print("vlog/input/ に動画がありません")
        return
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    parts = [make_part(i, s) for i, s in enumerate(scenes)]
    n = len(parts)

    # クロスフェードでつなげる
    inputs, chain = [], []
    for p, _ in parts:
        inputs += ["-i", p]
    last, offset = "[0:v]", 0.0
    for i in range(1, n):
        offset += parts[i - 1][1] - FADE
        out = f"[v{i}]"
        chain.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}{out}")
        last = out
    total = sum(l for _, l in parts) - FADE * (n - 1)
    chain.append(f"{last}fade=t=in:d=0.5,fade=t=out:st={total - 0.8:.3f}:d=0.8[vout]")

    # BGMがあれば付ける（最後はフェードアウト）
    bgm = next((p for p in glob.glob(os.path.join(BASE, "bgm.*"))), None)
    cmd = ["ffmpeg", "-y"] + inputs
    maps = ["-map", "[vout]"]
    if bgm:
        cmd += ["-i", bgm]
        chain.append(f"[{n}:a]atrim=0:{total:.3f},afade=t=in:d=0.5,"
                     f"afade=t=out:st={total - 1.5:.3f}:d=1.5[aout]")
        maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-filter_complex", ";".join(chain)] + maps + [
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-movflags", "+faststart", "-t", f"{total:.3f}", OUTPUT]
    run(cmd)
    print(f"完成: {OUTPUT}（{total:.1f}秒 / {n}カット）")


if __name__ == "__main__":
    main()

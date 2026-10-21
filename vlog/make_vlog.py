"""
縦型Vlogを自動で作るスクリプト

使い方:
  1. vlog/input/ に素材動画を入れる（ファイル名の順番に並びます）
  2. BGMを使うなら vlog/bgm.mp3 を置く（なくてもOK）
  3. python3 vlog/make_vlog.py を実行
  4. vlog/output/vlog.mp4 が完成品
"""
import glob
import os
import subprocess

# ===== 設定（ここを変えると仕上がりが変わる） =====
TARGET_SEC = 25      # 完成動画の目標の長さ（秒）
TRIM_HEAD = 0.4      # 各素材の「最初」に切り捨てる秒数（録画開始のブレ対策）
TRIM_TAIL = 0.4      # 各素材の「最後」に切り捨てる秒数（録画停止のブレ対策）
FADE = 0.3           # カット同士を重ねて切り替える秒数（クロスフェード）
WIDTH, HEIGHT = 1080, 1920   # 縦画面（9:16）
FPS = 30

# 色の雰囲気（おしゃれ寄り：少し淡く、少し暖かく、周りを少し暗く）
COLOR_GRADE = (
    "eq=saturation=0.85:contrast=1.05:brightness=0.02,"
    "colorbalance=rs=0.04:bs=-0.04:rm=0.02:bm=-0.02,"
    "vignette=PI/5"
)

BASE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE, "input")
WORK_DIR = os.path.join(BASE, "work")
OUTPUT = os.path.join(BASE, "output", "vlog.mp4")


def run(cmd):
    """ffmpegなどのコマンドを実行する（失敗したら止まる）"""
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def duration(path):
    """ffprobeで動画の長さ（秒）を調べる"""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main():
    # 1. 素材を集める
    exts = ("*.mp4", "*.mov", "*.MP4", "*.MOV", "*.m4v")
    clips = sorted(p for e in exts for p in glob.glob(os.path.join(INPUT_DIR, e)))
    if not clips:
        print("vlog/input/ に動画がありません")
        return
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    # 2. 1カットの長さを決める（全体が TARGET_SEC 秒になるように）
    n = len(clips)
    per_clip = (TARGET_SEC + FADE * (n - 1)) / n

    # 3. 各素材を「切る → 縦にそろえる → 色をつける」
    parts = []
    for i, src in enumerate(clips):
        usable = duration(src) - TRIM_HEAD - TRIM_TAIL
        length = max(0.8, min(per_clip, usable))
        dst = os.path.join(WORK_DIR, f"part{i:02d}.mp4")
        vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},{COLOR_GRADE},format=yuv420p"
        )
        run(["ffmpeg", "-y", "-ss", str(TRIM_HEAD), "-i", src, "-t", f"{length:.3f}",
             "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", dst])
        parts.append((dst, length))
        print(f"  カット{i + 1}: {os.path.basename(src)} → {length:.1f}秒使用")

    # 4. クロスフェードでつなげる
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

    # 5. BGMがあれば付ける（最後はフェードアウト）
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

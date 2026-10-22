"""
自分の動画のうしろに「説」の画像をつなぎ、画像のあいだだけ説のBGMを流すスクリプト

使い方:
  python3 suiyobi/join_setsu.py 自分の動画.mp4
  → output/JC卒業なぜかエモい説_完成.mp4 ができる
"""
import json
import os
import subprocess
import sys

# ===== 設定 =====
IMAGE = "output/JC卒業なぜかエモい説.png"      # つなぐ説の画像
BGM_SOURCE = "suiyobi/input/setsu_bgm.mov"     # BGMを切り取る元の動画
BGM_START = 0.0      # BGMを切り取りはじめる位置（秒）
BGM_END = 5.8        # BGMを切り取り終わる位置（秒）。画像もこの長さだけ出す
FADE_OUT = 0.3       # BGMの終わりをなめらかに消す長さ（秒）
OUTPUT = "output/JC卒業なぜかエモい説_完成.mp4"

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def probe(path):
    """動画のサイズ・コマ数・音があるかを ffprobe で調べる"""
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", path],
        capture_output=True, text=True, check=True).stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = int(video["width"]), int(video["height"])
    # スマホの縦動画は「横長＋90度回転」で保存されていることがあるので直す
    rot = 0
    for side in video.get("side_data_list", []):
        rot = int(side.get("rotation", 0))
    if abs(rot) == 90:
        w, h = h, w
    num, den = video["r_frame_rate"].split("/")
    fps = round(int(num) / int(den))
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    duration = float(video.get("duration", 0))
    return w, h, fps, has_audio, duration


def main(video):
    w, h, fps, has_audio, duration = probe(video)
    length = BGM_END - BGM_START
    print(f"元の動画: {w}x{h} {fps}fps 音{'あり' if has_audio else 'なし'}")

    # 画像を動画と同じ大きさにそろえる（はみ出さないよう縮めて、すきまは黒）
    fit = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={fps},format=yuv420p")

    inputs = ["-i", video,
              "-loop", "1", "-t", str(length), "-i", os.path.join(BASE, IMAGE),
              "-ss", str(BGM_START), "-t", str(length), "-i", os.path.join(BASE, BGM_SOURCE)]
    if not has_audio:                     # 音のない動画には無音をつけておく
        inputs += ["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=r=44100:cl=stereo"]
    main_audio = "[0:a]" if has_audio else "[3:a]"

    graph = (
        f"[0:v]{fit}[v0];"
        f"[1:v]{fit}[v1];"
        f"{main_audio}aresample=44100,aformat=channel_layouts=stereo[a0];"
        f"[2:a]aresample=44100,aformat=channel_layouts=stereo,"
        f"afade=t=out:st={length - FADE_OUT}:d={FADE_OUT}[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs,
           "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-crf", "20", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           os.path.join(BASE, OUTPUT)]
    subprocess.run(cmd, check=True)
    print("完成:", os.path.abspath(os.path.join(BASE, OUTPUT)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("使い方: python3 suiyobi/join_setsu.py 自分の動画.mp4")
    main(sys.argv[1])

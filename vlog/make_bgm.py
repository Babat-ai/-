"""
Lo-fi風のBGMをプログラムで作曲するスクリプト（著作権フリー）

使い方:
  python3 vlog/make_bgm.py
  → vlog/bgm.mp3 ができる（make_vlog.py が自動で使う）
"""
import os
import subprocess
import wave

import numpy as np

# ===== 設定 =====
BPM = 90             # テンポ（1分間に何拍か）
BARS = 6             # 何小節作るか（90BPMなら1小節 ≒ 2.67秒）
SR = 44100           # 1秒あたりのサンプル数（音の細かさ）
SEED = 7             # ノイズの乱数のタネ（同じ値なら毎回同じ音になる）

# コード進行（音の高さはMIDI番号: 60 = 真ん中のド）
CHORDS = [
    [53, 57, 60, 64],   # Fmaj7（ファ・ラ・ド・ミ）
    [52, 55, 59, 62],   # Em7  （ミ・ソ・シ・レ）
    [50, 53, 57, 60],   # Dm7  （レ・ファ・ラ・ド）
    [48, 52, 55, 59],   # Cmaj7（ド・ミ・ソ・シ）
    [53, 57, 60, 64],   # Fmaj7
    [48, 52, 55, 59],   # Cmaj7（ここで終わる）
]

BASE = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(BASE, "work")
OUTPUT = os.path.join(BASE, "bgm.mp3")

beat = 60 / BPM
bar = beat * 4
total = bar * BARS + 2.0          # 最後の和音の余韻ぶん少し長めに
rng = np.random.default_rng(SEED)


def freq(midi):
    """MIDI番号を周波数（Hz）に変換する"""
    return 440 * 2 ** ((midi - 69) / 12)


def place(track, sound, at):
    """track の at 秒の位置に sound を重ねる"""
    i = int(at * SR)
    end = min(len(track), i + len(sound))
    track[i:end] += sound[: end - i]


def keys_note(midi, length):
    """エレピ風の音（倍音を足して、だんだん小さくなる）"""
    t = np.arange(int(length * SR)) / SR
    f = freq(midi)
    tone = (np.sin(2 * np.pi * f * t)
            + 0.4 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3)
            + 0.15 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 6))
    tone *= 1 + 0.003 * np.sin(2 * np.pi * 5 * t)     # わずかな揺れ（テープ感）
    env = np.minimum(t / 0.01, 1) * np.exp(-t * 0.9)  # 立ち上がり→ゆっくり減衰
    return tone * env


def bass_note(midi, length):
    """ベース（低いサイン波）"""
    t = np.arange(int(length * SR)) / SR
    env = np.minimum(t / 0.02, 1) * np.exp(-t * 1.5)
    return np.sin(2 * np.pi * freq(midi) * t) * env


def kick():
    """キック（周波数が下がっていくサイン波＝「ドン」）"""
    t = np.arange(int(0.4 * SR)) / SR
    f = 50 + 80 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def snare():
    """スネア（ノイズ＋少しの音程＝「タッ」）"""
    t = np.arange(int(0.25 * SR)) / SR
    noise = rng.uniform(-1, 1, len(t))
    noise = noise - np.convolve(noise, np.ones(8) / 8, mode="same")   # 低音を削る
    return (0.6 * noise + 0.4 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 18)


def hihat():
    """ハイハット（高い音だけのノイズ＝「チッ」）"""
    t = np.arange(int(0.06 * SR)) / SR
    noise = rng.uniform(-1, 1, len(t))
    noise = noise - np.convolve(noise, np.ones(4) / 4, mode="same")
    return noise * np.exp(-t * 60)


def main():
    n = int(total * SR)
    keys, bass, drums = np.zeros(n), np.zeros(n), np.zeros(n)

    for b, chord in enumerate(CHORDS):
        start = b * bar
        last = b == len(CHORDS) - 1
        length = bar + (2.0 if last else 0.3)
        # 和音を少しずつずらして弾く（人が弾いたような感じになる）
        for k, midi in enumerate(chord):
            place(keys, keys_note(midi + 12, length) * 0.18, start + k * 0.025)
        place(bass, bass_note(chord[0] - 12, beat * 2.5) * 0.5, start)
        if not last:
            place(bass, bass_note(chord[0] - 12, beat * 1.5) * 0.4, start + beat * 2.5)

        # 1小節目と最後の小節はドラムなし（静かに始まって、静かに終わる）
        if b == 0 or last:
            continue
        for i in range(8):                          # 8分音符ごと
            at = start + i * beat / 2
            if i % 2 == 1:
                at += beat * 0.08                   # 裏拍を少し遅らせる（スウィング）
            place(drums, hihat() * (0.12 if i % 2 == 0 else 0.07), at)
        place(drums, kick() * 0.8, start)
        place(drums, kick() * 0.6, start + beat * 2.5)
        place(drums, snare() * 0.35, start + beat)
        place(drums, snare() * 0.35, start + beat * 3)

    # レコードのパチパチ音
    crackle = np.zeros(n)
    pops = rng.random(n) < 0.0004
    crackle[pops] = rng.uniform(-1, 1, pops.sum()) * 0.15
    crackle += rng.normal(0, 0.004, n)

    mix = keys + bass + drums + crackle
    mix = mix / np.max(np.abs(mix)) * 0.8

    os.makedirs(WORK_DIR, exist_ok=True)
    wav_path = os.path.join(WORK_DIR, "bgm.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

    # ffmpegで仕上げ：こもった音（高音カット）＋ 響き（エコー）＋ 音量をそろえる
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", wav_path, "-af",
         "lowpass=f=3800,aecho=0.8:0.6:60|120:0.25|0.15,loudnorm=I=-16:TP=-1.5",
         "-ac", "2", "-ar", "44100", "-b:a", "192k", OUTPUT],
        check=True,
    )
    print(f"完成: {OUTPUT}（{total:.1f}秒 / {BPM}BPM / {BARS}小節）")


if __name__ == "__main__":
    main()

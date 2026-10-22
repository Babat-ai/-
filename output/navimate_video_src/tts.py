# ナレーション音声の生成（VOICEVOX:No.7）＋ タイムライン・口パク用データの作成
import json, wave, io, os
import numpy as np
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

V = os.environ.get("VV", "vv/")
ort = Onnxruntime.load_once(filename=V + "voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so")
syn = Synthesizer(ort, OpenJtalk(V + "open_jtalk_dic_utf_8-1.11"))
with VoiceModelFile.open(V + "vvms/6.vvm") as m:
    syn.load_voice_model(m)

SID = 29          # No.7 ノーマル
SR = 24000
GAP = 0.34        # 文と文の間
LEAD, TAIL = 0.45, 0.75
LONG = {"op": (1.6, 0.9), "ch1": (1.2, 1.2), "ch2": (1.2, 1.2), "end": (0.6, 3.0)}
FPS = 30

voice = []
scenes = []
t_global = 0.0
for s in json.load(open("script.json")):
    lead, tail = LONG.get(s["id"], (LEAD, TAIL))
    segs = [np.zeros(int(lead * SR), dtype=np.int16)]
    t = lead
    subs = []
    for i, p in enumerate(s["parts"]):
        sub, txt = (p["s"], p["t"]) if isinstance(p, dict) else (p, p)
        q = syn.create_audio_query(txt, SID)
        q.speed_scale = s.get("speed", 1.13)
        q.pitch_scale = 0.01
        q.intonation_scale = 1.18
        q.pre_phoneme_length = 0.03
        q.post_phoneme_length = 0.05
        w = syn.synthesis(q, SID)
        with wave.open(io.BytesIO(w)) as f:
            a = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
        d = len(a) / SR
        subs.append({"t": round(t, 3), "d": round(d, 3), "s": sub})
        segs.append(a)
        t += d
        if i < len(s["parts"]) - 1:
            segs.append(np.zeros(int(GAP * SR), dtype=np.int16))
            t += GAP
    segs.append(np.zeros(int(tail * SR), dtype=np.int16))
    a = np.concatenate(segs)
    dur = len(a) / SR
    scenes.append({"id": s["id"], "start": round(t_global, 3), "dur": round(dur, 3), "subs": subs})
    voice.append(a)
    t_global += dur
    print(f'{s["id"]:8s} {dur:6.2f}s  -> {t_global:6.2f}')

v = np.concatenate(voice)
os.makedirs("voice", exist_ok=True)
with wave.open("voice/voice.wav", "wb") as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(v.tobytes())

# 口パク：1フレームごとの音量（0〜1）
hop = SR // FPS
x = v.astype(np.float32) / 32768
n = len(x) // hop
rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1))
mouth = np.clip(rms / 0.09, 0, 1)
mouth = np.round(mouth, 2).tolist()

total = round(t_global, 2)
json.dump({"total": total, "fps": FPS, "scenes": scenes, "mouth": mouth},
          open("voice/timeline.json", "w"), ensure_ascii=False)
print("total", total, "sec =", f"{int(total//60)}:{total%60:05.2f}")

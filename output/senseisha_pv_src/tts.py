import json, wave, io
import numpy as np
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
V="vv/"
ort=Onnxruntime.load_once(filename=V+"voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so")
syn=Synthesizer(ort, OpenJtalk(V+"open_jtalk_dic_utf_8-1.11"))
with VoiceModelFile.open(V+"vvms/6.vvm") as m: syn.load_voice_model(m)
SID=30; SR=24000; GAP=0.32
out={}
for s in json.load(open("script.json")):
    segs=[]; marks=[]; t=0
    for i,p in enumerate(s["parts"]):
        q = syn.create_audio_query_from_kana(p[5:],SID) if p.startswith("kana:") else syn.create_audio_query(p,SID)
        q.speed_scale=s.get("speed",1.07); q.pre_phoneme_length=0.03; q.post_phoneme_length=0.05; q.intonation_scale=1.12
        w=syn.synthesis(q,SID)
        with wave.open(io.BytesIO(w)) as f: SR=f.getframerate(); a=np.frombuffer(f.readframes(f.getnframes()),dtype=np.int16)
        marks.append(round(t,2)); segs.append(a); t+=len(a)/SR
        if i<len(s["parts"])-1:
            segs.append(np.zeros(int(GAP*SR),dtype=np.int16)); t+=GAP
    a=np.concatenate(segs)
    with wave.open(f"voice/{s['id']}.wav","wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(a.tobytes())
    out[s["id"]]={"dur":round(len(a)/SR,2),"marks":marks}; print(s["id"],out[s["id"]])
print("total",round(sum(v["dur"] for v in out.values()),2))
json.dump(out,open("voice/durations.json","w"))

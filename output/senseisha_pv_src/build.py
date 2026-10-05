import json
d={k:v for k,v in json.load(open("../voice/durations.json")).items()}
h=open("index.html").read().replace("__DURATIONS__",json.dumps(d)).replace("__SUBS__",json.dumps(json.load(open("subs.json")),ensure_ascii=False))
open("render.html","w").write(h)

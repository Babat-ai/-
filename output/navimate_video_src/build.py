import json
h = open("index.html").read()
h = h.replace("__TL__", open("voice/timeline.json").read()).replace("__CHARA__", open("character.svg.html").read())
open("render.html", "w").write(h)

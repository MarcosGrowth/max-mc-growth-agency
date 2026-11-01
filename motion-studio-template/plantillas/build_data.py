"""Genera composition/assets/data.js para un reel: frases con tiempos por palabra, palabras destacadas
y la envolvente de la voz (30 fps).

Copiar a proyectos/<reel>/build_data.py. Lee timeline.json:
  "lineas":  {"l1": 0.3, ...}          segundo en que arranca cada línea de voz
  "frases":  [{"linea": "l1", "desde": 0, "hasta": 4}, ...]   cómo se parte cada línea en pantalla
  "acentos": ["palabra", ...]          palabras que van destacadas (color de acento)
"""
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE / "timeline.json").read_text())
W = json.loads((HERE / "audio/vo/words.json").read_text())
ACC, FPS = {a.lower() for a in TL.get("acentos", [])}, 30


def toks(text):
    return [t for t in re.split(r"\s+", text.replace("…", "… ")) if re.search(r"\w", t)]


frases = []
for f in TL["frases"]:
    line, start = W[f["linea"]], TL["lineas"][f["linea"]]
    tk = toks(line["text"])
    assert len(tk) == len(line["words"]), (f["linea"], tk)
    rng = range(f.get("desde", 0), f.get("hasta", len(tk)))
    frases.append({"t": round(start + max(0, line["words"][rng[0]]["t"]) - 0.05, 3),
                   "words": [{"w": tk[i], "t": round(start + max(0, line["words"][i]["t"]), 3),
                              "a": line["words"][i]["w"].lower() in ACC} for i in rng]})
for a, b in zip(frases, frases[1:]):
    a["end"] = round(b["t"] - 0.08, 3)
if frases:
    last = max(TL["lineas"], key=TL["lineas"].get)
    frases[-1]["end"] = round(TL["lineas"][last] + W[last]["dur"] + 0.4, 3)

absw = {lid: {} for lid in W}
for lid, line in W.items():
    seen = {}
    for w in line["words"]:
        k = w["w"].lower()
        absw[lid][k if k not in seen else f"{k}#{seen[k]}"] = round(TL["lineas"][lid] + max(0, w["t"]), 3)
        seen[k] = seen.get(k, 0) + 1

env = np.zeros(int(TL["duracion"] * FPS))
for lid, st in TL["lineas"].items():
    a, sr = sf.read(HERE / "audio/vo" / f"{lid}.wav")
    hop = sr // FPS
    for i in range(len(a) // hop):
        j = int(st * FPS) + i
        if j < len(env):
            env[j] = max(env[j], float(np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2))))
env = np.clip(env / (env.max() or 1), 0, 1)
(HERE / "composition/assets/data.js").write_text(
    "// Generado por build_data.py — no editar a mano\nwindow.REEL = "
    + json.dumps({"tl": TL, "frases": frases, "w": absw, "env": [round(x, 3) for x in env]}, ensure_ascii=False) + ";\n")
print("frases:", len(frases))

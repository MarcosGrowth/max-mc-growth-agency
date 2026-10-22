"""Genera composition/assets/data.js para el reel 3: frases con tiempos por palabra, acentos,
tiempos absolutos de palabras y la envolvente de la voz (30 fps) para el indicador de "hablando".
Uso: python3 video3/build_data.py
"""
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE / "timeline.json").read_text())
W = json.loads((HERE / "audio/vo/words.json").read_text())
ACC = set(TL["acentos"])
FPS = 30


def toks(text):
    return [t for t in re.split(r"\s+", text.replace("…", "… ")) if re.search(r"\w", t)]


frases = []
for f in TL["frases"]:
    lid = f["linea"]
    line, start = W[lid], TL["lineas"][lid]
    tk = toks(line["text"])
    assert len(tk) == len(line["words"]), (lid, tk, [w["w"] for w in line["words"]])
    rng = range(f["desde"], f.get("hasta", len(tk)))
    frases.append({"t": round(start + max(0, line["words"][rng[0]]["t"]) - 0.05, 3),
                   "words": [{"w": tk[i], "t": round(start + max(0, line["words"][i]["t"]), 3),
                              "a": line["words"][i]["w"].lower() in ACC} for i in rng]})
for a, b in zip(frases, frases[1:]):
    a["end"] = round(b["t"] - 0.08, 3)
frases[-1]["end"] = round(TL["lineas"]["a9"] - 0.3, 3)

absw = {}
for lid, line in W.items():
    seen = {}
    for w in line["words"]:
        k = w["w"].lower()
        key = k if k not in seen else f"{k}#{seen[k]}"
        seen[k] = seen.get(k, 0) + 1
        absw.setdefault(lid, {})[key] = round(TL["lineas"][lid] + max(0, w["t"]), 3)

env = np.zeros(int(TL["duracion"] * FPS))
for lid, st in TL["lineas"].items():
    a, sr = sf.read(HERE / "audio/vo" / f"{lid}.wav")
    hop = sr // FPS
    for i in range(len(a) // hop):
        j = int(st * FPS) + i
        if j < len(env):
            env[j] = max(env[j], float(np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2))))
env = np.clip(env / (env.max() or 1), 0, 1)

data = {"tl": TL, "frases": frases, "w": absw, "env": [round(x, 3) for x in env]}
(HERE / "composition/assets/data.js").write_text("// Generado por video3/build_data.py — no editar a mano\nwindow.R3 = " + json.dumps(data, ensure_ascii=False) + ";\n")
for f in frases:
    print(f["t"], f["end"], " ".join(("*" + w["w"] + "*") if w["a"] else w["w"] for w in f["words"]))

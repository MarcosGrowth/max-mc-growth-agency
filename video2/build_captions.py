"""Genera composition/assets/captions.js: subtítulos tipo karaoke del reel 2 a partir de los tiempos de la voz.

Los cortes de cada línea salen de timeline.json ("cortes"); si faltan, cada bloque tiene 1 a 3 palabras, empieza cuando se dice su primera palabra y dura hasta el bloque siguiente.
El tamaño de letra se calcula para que el bloque entre en 900 px de ancho.
Uso: python3 video2/build_captions.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE / "timeline.json").read_text())
WORDS = json.loads((HERE / "audio/vo/words.json").read_text())
COLOR = {w: c for c, ws in TL["resaltar"].items() for w in ws}
MAXW, MAXFS, MINFS = 900, 120, 70


def tokens_with_punct(text):
    return [t for t in re.split(r"\s+", text.replace("…", "… ")) if re.search(r"\w", t)]


def chunks_for(line_id, start):
    line = WORDS[line_id]
    toks = tokens_with_punct(line["text"])
    words = line["words"]
    punct = [bool(re.search(r"[.,:;?!…]$", t)) for t in toks] if len(toks) == len(words) else [False] * len(words)
    out, cur = [], []
    if line_id in TL.get("cortes", {}):
        sizes = TL["cortes"][line_id]
        assert sum(sizes) == len(words), (line_id, sizes, len(words))
        i = 0
        for n in sizes:
            out.append(list(range(i, i + n)))
            i += n
        words_iter = []
    else:
        words_iter = list(enumerate(words))
    for i, w in words_iter:
        cur.append(i)
        nxt_gap = (words[i + 1]["t"] - (w["t"] + w["d"])) if i + 1 < len(words) else 9
        chars = sum(len(words[j]["w"]) for j in cur)
        if punct[i] or nxt_gap > 0.22 or len(cur) == 3 or chars >= 14 or i + 1 == len(words):
            out.append(cur)
            cur = []
    res = []
    for k, idx in enumerate(out):
        t0 = start + max(0.0, words[idx[0]]["t"])
        t1 = start + (words[out[k + 1][0]]["t"] if k + 1 < len(out) else line["dur"] + 0.25)
        ws = [{"w": words[j]["w"].upper(), "c": COLOR.get(words[j]["w"].lower(), "")} for j in idx]
        text = " ".join(x["w"] for x in ws)
        fs = max(MINFS, min(MAXFS, int(MAXW / (len(text) * 0.66))))
        res.append({"t": round(t0, 3), "end": round(t1, 3), "fs": fs, "words": ws})
    return res


caps = {h: chunks_for(h, TL["hook_start"]) for h in ("h1", "h2", "h3")}
caps["body"] = [c for lid, st in TL["lineas"].items() for c in chunks_for(lid, st)]
# el último bloque de cada línea no debe pisar el comienzo de la línea siguiente
body = caps["body"]
for a, b in zip(body, body[1:]):
    a["end"] = min(a["end"], b["t"])
words_abs = {
    lid: {w["w"].lower() + (f"#{k}" if k else ""): round((TL["hook_start"] if lid.startswith("h") else TL["lineas"][lid]) + w["t"], 3)
          for k_all, w in enumerate(WORDS[lid]["words"])
          for k in [sum(1 for x in WORDS[lid]["words"][:k_all] if x["w"].lower() == w["w"].lower())]}
    for lid in WORDS
}
js = "// Generado por video2/build_captions.py — no editar a mano\n"
js += "window.R2 = " + json.dumps({"caps": caps, "w": words_abs, "tl": TL}, ensure_ascii=False) + ";\n"
(HERE / "composition/assets/captions.js").write_text(js)
print("bloques:", {k: len(v) for k, v in caps.items()})
for c in caps["body"][:12]:
    print(c["t"], c["end"], c["fs"], " ".join(w["w"] for w in c["words"]))

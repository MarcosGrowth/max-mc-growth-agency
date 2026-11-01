"""Voz en off con tiempos por palabra (Microsoft Edge TTS, sin key).

Uso:  python3 tools/voz/make_vo.py proyectos/<reel>/audio/vo
Lee <carpeta>/lines.tsv (id<TAB>velocidad<TAB>texto), escribe <id>.wav (48 kHz mono, sin silencios en los
extremos) y words.json con las palabras de cada línea en segundos.
Voz: variable VOZ (por defecto es-AR-TomasNeural; otras: es-AR-ElenaNeural, es-MX-JorgeNeural, es-ES-AlvaroNeural…).
Ver voces: edge-tts --list-voices | grep es-
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import edge_tts

DIR = Path(sys.argv[1]).resolve()
VOICE = os.environ.get("VOZ", "es-AR-TomasNeural")


async def synth(line_id, rate, text):
    com = edge_tts.Communicate(text, VOICE, rate=rate, boundary="WordBoundary", proxy=os.environ.get("HTTPS_PROXY"))
    audio, words = bytearray(), []
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append({"w": ch["text"], "t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7})
    mp3 = DIR / f"{line_id}.mp3"
    mp3.write_bytes(audio)
    lead = max(0.0, words[0]["t"] - 0.03) if words else 0.0
    wav = DIR / f"{line_id}.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{lead:.3f}", "-i", str(mp3),
                    "-af", "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                    "-ar", "48000", "-ac", "1", str(wav)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                               capture_output=True, text=True).stdout)
    for w in words:
        w["t"], w["d"] = round(w["t"] - lead, 3), round(w["d"], 3)
    return {"id": line_id, "text": text, "dur": round(dur, 3), "words": words}


async def main():
    rows = [l.split("\t") for l in (DIR / "lines.tsv").read_text().splitlines() if l.strip()]
    out = {}
    for line_id, rate, text in rows:
        out[line_id] = await synth(line_id, rate, text)
        print(line_id, out[line_id]["dur"], "s")
    (DIR / "words.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


asyncio.run(main())

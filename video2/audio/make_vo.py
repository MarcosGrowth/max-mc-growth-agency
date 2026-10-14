"""Voz en off del reel 2 (es-AR, Tomás) con tiempos por palabra para los subtítulos.

Salidas en vo/: <id>.wav (48 kHz mono, sin silencios en los extremos) y words.json
con las palabras de cada línea en segundos relativos al inicio del WAV.
Uso: python3 video2/audio/make_vo.py   (requiere: pip install edge-tts)
"""
import asyncio
import json
import os
import subprocess
from pathlib import Path

import edge_tts

HERE = Path(__file__).resolve().parent / "vo"
VOICE = "es-AR-TomasNeural"


async def synth(line_id, rate, text):
    proxy = os.environ.get("HTTPS_PROXY")
    com = edge_tts.Communicate(text, VOICE, rate=rate, boundary="WordBoundary", proxy=proxy)
    audio = bytearray()
    words = []
    async for chunk in com.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            words.append({"w": chunk["text"], "t": chunk["offset"] / 1e7, "d": chunk["duration"] / 1e7})
    mp3 = HERE / f"{line_id}.mp3"
    mp3.write_bytes(audio)
    # recorta el silencio inicial y desplaza las palabras en la misma cantidad
    probe = subprocess.run(["ffmpeg", "-nostdin", "-i", str(mp3), "-af", "silencedetect=n=-45dB:d=0.02", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    lead = 0.0
    for ln in probe.splitlines():
        if "silence_end" in ln:
            t_end = float(ln.split("silence_end:")[1].split("|")[0])
            start_line = [l for l in probe.splitlines() if "silence_start" in l]
            if start_line and float(start_line[0].split("silence_start:")[1]) <= 0.01:
                lead = max(0.0, t_end - 0.03)
            break
    wav = HERE / f"{line_id}.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{lead:.3f}", "-i", str(mp3),
                    "-af", "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                    "-ar", "48000", "-ac", "1", str(wav)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                               capture_output=True, text=True).stdout)
    for w in words:
        w["t"] = round(w["t"] - lead, 3)
        w["d"] = round(w["d"], 3)
    return {"id": line_id, "text": text, "dur": round(dur, 3), "words": words}


async def main():
    rows = [l.split("\t") for l in (HERE / "lines.tsv").read_text().splitlines() if l.strip()]
    out = {}
    for line_id, rate, text in rows:
        out[line_id] = await synth(line_id, rate, text)
        print(line_id, out[line_id]["dur"], len(out[line_id]["words"]))
    (HERE / "words.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


asyncio.run(main())

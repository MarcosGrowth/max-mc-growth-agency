"""Banda sonora del reel 3 "Que te compren": música original cálida + efectos + voz, mezcla a −14 LUFS.

Reutiliza los instrumentos del reel 1 (video/audio/build_audio.py). Todo es determinista.
Salidas: video3/audio/out/mix.wav y music.wav.  Uso: python3 video3/audio/build_audio.py
"""
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("synth1", ROOT / "video/audio/build_audio.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

SR = S.SR
TL = json.loads((ROOT / "video3/timeline.json").read_text())
WORDS = json.loads((HERE / "vo/words.json").read_text())
DUR = TL["duracion"]
N = int(DUR * SR)
BEAT = 60 / TL["bpm"]
LN, ES = TL["lineas"], TL["escenas"]
SFX = ROOT / ".agents/skills/brag/assets/sfx"
OUT = HERE / "out"


def wt(line, word, n=0):
    hits = [w for w in WORDS[line]["words"] if w["w"].lower() == word.lower()]
    return LN[line] + max(0.0, hits[n]["t"])


def build_music():
    L = np.zeros(N)
    R = np.zeros(N)

    def both(sig, at, g=1.0, pan=0.0):
        S.place(L, sig, at, g * (1 - max(pan, 0)))
        S.place(R, sig, at, g * (1 + min(pan, 0)))

    n = S.note
    # progresión cálida en La mayor relativo: F#m – D – A – E
    prog = [["F#3", "A3", "C#4"], ["D3", "F#3", "A3"], ["A3", "C#4", "E4"], ["E3", "G#3", "B3"]]
    roots = ["F#1", "D1", "A1", "E1"]
    bar = BEAT * 4
    t_sys, t_cierre = ES["embudo"], ES["cierre"]
    t_final = LN["a9"]

    t = 0.0
    bi = 0
    while t < t_final - 0.05:
        ch = prog[bi % 4]
        tension = ES["rebote"] <= t < t_sys
        both(S.pad([n(x) for x in ch], bar + 0.4, 900 if tension else 1800), t, 0.45)
        for s in range(8):
            ts = t + s * BEAT / 2
            if ts >= t_final - 0.05:
                break
            # arpegio suave en corcheas (más apagado durante la tensión)
            both(S.pluck(n(ch[[0, 1, 2, 1][s % 4]]) * 2, 0.45, 2200 if tension else 3600), ts, 0.13, pan=-0.35 if s % 2 else 0.35)
            if ts >= t_sys:  # el pulso entra cuando aparece el sistema
                if s % 4 == 0:
                    both(S.kick() * 0.7, ts, 0.6)
                if s % 4 == 2:
                    both(S.clap() * 0.6, ts, 0.3)
                both(S.hat(), ts + BEAT / 4, 0.07, pan=0.3)
            if s % 4 == 0:
                both(S.bass_note(n(roots[bi % 4]), BEAT * 1.8), ts, 0.38 if ts >= t_sys else 0.22)
        t += bar
        bi += 1
    both(S.riser(1.4), t_sys - 1.4, 0.3)
    both(S.impact(1.4) * 0.5, t_sys, 0.5)
    # cierre: silencio breve antes de "Que te compren." y resolución en La mayor
    both(S.riser(t_final - t_cierre), t_cierre, 0.28)
    tail = DUR - t_final
    both(S.impact(2.4) * 0.8, t_final, 0.8)
    both(S.pad([n("A2"), n("E3"), n("A3"), n("C#4"), n("E4")], tail, 2600), t_final, 0.75)
    for k, x in enumerate(["A4", "C#5", "E5", "A5"]):
        both(S.pluck(n(x), 0.9, 4800), t_final + 0.4 + k * BEAT / 2, 0.14, pan=0.4 if k % 2 else -0.4)
    for k in range(int((tail - 0.8) / BEAT)):
        ts = t_final + 0.8 + k * BEAT
        both(S.kick() * 0.5, ts, 0.45)
        both(S.bass_note(n("A1"), BEAT * 0.9), ts, 0.3)

    music = np.stack([S.reverb(L, 1.8, 0.2), S.reverb(R, 1.9, 0.2)], axis=1)
    music *= np.minimum((DUR - S.t_axis(DUR)) / 1.5, 1.0)[:, None]
    return music / np.max(np.abs(music)) * 0.8


def sfx_list():
    keys = [f"keyboard/keypress-0{10 + i:02d}.wav" for i in range(14)]
    s = [(keys[i], 0.1 + i * 0.05, -16) for i in range(14)]  # tipeo del prompt
    s += [
        ("interface/switch_005.ogg", 0.75, -13),                       # aparece el anuncio
        ("synth:whoosh", wt("a2", "cualquiera") - 0.15, -12),          # tachado
        ("interface/drop_002.ogg", ES["rebote"] + 0.1, -15),
        ("synth:whoosh", ES["embudo"] - 0.3, -10),
        ("synth:whoosh", ES["diagnostico"] - 0.3, -11),
        ("interface/switch_002.ogg", wt("a6", "anuncios"), -12),
        ("interface/switch_002.ogg", wt("a6", "landing"), -12),
        ("interface/switch_002.ogg", wt("a6", "respondés"), -12),
        ("interface/select_008.ogg", wt("a7", "escapan"), -12),
        ("synth:whoosh", ES["llamada"] - 0.3, -11),
        ("interface/bong_001.ogg", ES["llamada"] + 0.2, -13),          # entra la llamada
        ("ui/rollover2.ogg", wt("a8", "gratis"), -12),
        ("ui/rollover2.ogg", wt("a8", "compromiso"), -12),
        ("synth:whoosh", ES["cierre"] - 0.1, -10),
        ("interface/switch_005.ogg", LN["a9"] + 1.2, -13),             # botón CTA
    ]
    return s


def build_sfx():
    buf = np.zeros((N, 2))
    for f, t, g in sfx_list():
        sig = np.stack([S.whoosh()] * 2, axis=1) * 0.6 if f == "synth:whoosh" else S.load_audio(SFX / f)
        i = int(t * SR)
        j = min(N, i + len(sig))
        buf[i:j] += sig[: j - i] * S.db(g)
    return buf


def build_vo():
    buf = np.zeros((N, 2))
    for lid, start in LN.items():
        sig, _ = sf.read(HERE / "vo" / f"{lid}.wav")
        sig = S.hp(sig, 90)
        i = int(start * SR)
        j = min(N, i + len(sig))
        buf[i:j] += sig[: j - i, None]
    return buf


def main():
    OUT.mkdir(exist_ok=True)
    music = build_music()
    sf.write(OUT / "music.wav", music, SR, subtype="PCM_24")
    vo = build_vo()
    vo = vo / np.max(np.abs(vo)) * 0.9
    mix = vo + music * S.duck_curve(vo) * 0.5 + build_sfx() * 0.8
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    raw = OUT / "mix_raw.wav"
    sf.write(raw, mix, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.0:LRA=9",
                    "-ar", str(SR), "-c:a", "pcm_s24le", str(OUT / "mix.wav")], check=True)
    print("ok:", OUT / "mix.wav")


if __name__ == "__main__":
    main()

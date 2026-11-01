"""Ejemplo de banda sonora de un reel: música original + efectos + voz → mezcla a −14 LUFS.

Copiar a proyectos/<reel>/audio/build_audio.py y ajustar: progresión, BPM, momentos y efectos.
Lee proyectos/<reel>/timeline.json ({"duracion", "bpm", "lineas": {id: segundo}, "escenas": {...}}).
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent                 # proyectos/<reel>/audio
sys.path.insert(0, str(HERE.parents[2] / "tools/audio"))
import synth as S  # noqa: E402

TL = json.loads((HERE.parent / "timeline.json").read_text())
SR, DUR = S.SR, TL["duracion"]
N, BEAT = int(DUR * SR), 60 / TL["bpm"]


def build_music():
    L, R = np.zeros(N), np.zeros(N)

    def both(sig, at, g=1.0, pan=0.0):
        S.place(L, sig, at, g * (1 - max(pan, 0)))
        S.place(R, sig, at, g * (1 + min(pan, 0)))

    n = S.note
    prog = [["A3", "C4", "E4"], ["F3", "A3", "C4"], ["C4", "E4", "G4"], ["G3", "B3", "D4"]]  # Am–F–C–G
    t, bi = 0.0, 0
    while t < DUR - 1.5:
        ch = prog[bi % 4]
        both(S.pad([n(x) for x in ch], BEAT * 4 + 0.3, 1800), t, 0.45)
        for s in range(8):
            ts = t + s * BEAT / 2
            both(S.pluck(n(ch[[0, 1, 2, 1][s % 4]]) * 2, 0.4, 3600), ts, 0.13, pan=-0.3 if s % 2 else 0.3)
            if s % 4 == 0:
                both(S.kick() * 0.7, ts, 0.6)
                both(S.bass_note(n("A1"), BEAT * 1.8), ts, 0.3)
            if s % 4 == 2:
                both(S.clap() * 0.6, ts, 0.3)
        t += BEAT * 4
        bi += 1
    both(S.impact(2.0), DUR - 2.5, 0.8)
    music = np.stack([S.reverb(L, 1.6, 0.18), S.reverb(R, 1.7, 0.18)], axis=1)
    music *= np.minimum((DUR - S.t_axis(DUR)) / 1.2, 1.0)[:, None]
    return music / np.max(np.abs(music)) * 0.8


SFX = [  # (archivo dentro de .claude/skills/brag/assets/sfx | "synth:whoosh", segundo, ganancia dB)
    ("synth:whoosh", 0.0, -10),
]


def main():
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    music = build_music()
    vo = np.zeros((N, 2))
    for lid, start in TL["lineas"].items():
        sig, _ = sf.read(HERE / "vo" / f"{lid}.wav")
        i = int(start * SR)
        j = min(N, i + len(sig))
        vo[i:j] += S.hp(sig, 90)[: j - i, None]
    vo = vo / (np.max(np.abs(vo)) or 1) * 0.9
    sfx = np.zeros((N, 2))
    for f, t, g in SFX:
        sig = np.stack([S.whoosh()] * 2, axis=1) * 0.6 if f == "synth:whoosh" else S.load_audio(S.SFX_DIR / f)
        i = int(t * SR)
        j = min(N, i + len(sig))
        sfx[i:j] += sig[: j - i] * S.db(g)
    mix = vo + music * S.duck_curve(vo) * 0.5 + sfx * 0.8
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    sf.write(out / "mix_raw.wav", mix, SR, subtype="PCM_24")
    S.loudnorm(out / "mix_raw.wav", out / "mix.wav")
    print("ok:", out / "mix.wav")


if __name__ == "__main__":
    main()

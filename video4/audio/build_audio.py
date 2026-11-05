"""Música del manifiesto MC Growth: cada cuadro de timeline.json cae en un golpe; el ritmo acelera
hasta "crecimiento.", impacto en el logo y colchón para el cierre. Sin voz. Mezcla a −14 LUFS.
Uso: python3 video4/audio/build_audio.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "motion-studio-template/tools/audio"))
import synth as S  # noqa: E402

SFX = ROOT / ".agents/skills/brag/assets/sfx"
TL = json.loads((HERE.parent / "timeline.json").read_text())
SR, DUR = S.SR, TL["duracion"]
N = int(DUR * SR)


def main():
    L, R = np.zeros(N), np.zeros(N)

    def both(sig, at, g=1.0, pan=0.0):
        S.place(L, sig, at, g * (1 - max(pan, 0)))
        S.place(R, sig, at, g * (1 + min(pan, 0)))

    n = S.note
    cuadros = TL["cuadros"]
    t_logo, t_cta = TL["logo"], TL["cta"]
    roots = ["D1", "D1", "A#0", "A#0", "F1", "F1", "C1", "C1"]
    # golpe en cada cuadro: kick + bajo; clap en los impares; hats que se densifican
    for i, c in enumerate(cuadros):
        t = c["t"]
        nxt = cuadros[i + 1]["t"] if i + 1 < len(cuadros) else t_logo
        both(S.kick(), t, 0.95)
        both(S.bass_note(n(roots[(i // 2) % len(roots)]), max(0.15, nxt - t - 0.03)), t, 0.5)
        if i % 2:
            both(S.clap(), t, 0.4)
        sub = 4 if nxt - t > 0.5 else 2
        for k in range(sub):
            both(S.hat(), t + (nxt - t) * k / sub, 0.12 if k else 0.18, pan=0.35 if k % 2 else -0.35)
        if c.get("tipeo"):
            both(S.load_audio(SFX / "keyboard/keypress-012.wav")[:, 0] * 0.5, t + 0.04, 0.6)
        if any(l.startswith("*") for l in c["lineas"]):
            both(S.impact(1.0) * 0.5, t, 0.5)
    # pad tenso de fondo y riser hacia el remate
    both(S.pad([n("D3"), n("F3"), n("A3")], cuadros[-1]["t"] + 0.6, 1400), 0, 0.3)
    both(S.riser(t_logo - 5.0), 5.0, 0.4)
    # logo: corte de silencio corto y gran impacto + despegue
    both(S.impact(2.6), t_logo, 1.0)
    both(S.whoosh(0.9) * 0.8, t_logo + 0.15, 0.6)
    tail = DUR - t_logo
    both(S.pad([n("F2"), n("C3"), n("F3"), n("A3"), n("C4")], tail, 2400), t_logo, 0.7)
    for k, x in enumerate(["F4", "A4", "C5", "F5"]):
        both(S.pluck(n(x), 0.8, 5000), t_logo + 0.5 + k * 0.25, 0.14, pan=0.4 if k % 2 else -0.4)
    for k in range(int((DUR - t_cta) / 0.5)):
        both(S.kick() * 0.5, t_cta + k * 0.5, 0.45)
    mix = np.stack([S.reverb(L, 1.4, 0.15), S.reverb(R, 1.5, 0.15)], axis=1)
    mix *= np.minimum((DUR - S.t_axis(DUR)) / 0.8, 1.0)[:, None]
    mix = np.tanh(mix / np.max(np.abs(mix)) * 1.2) / np.tanh(1.2)
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    sf.write(out / "mix_raw.wav", mix, SR, subtype="PCM_24")
    S.loudnorm(out / "mix_raw.wav", out / "mix.wav")
    print("ok:", out / "mix.wav")


if __name__ == "__main__":
    main()

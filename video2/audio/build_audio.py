"""Banda sonora del reel 2: música original + efectos + voz, una mezcla por versión de gancho.

Reutiliza los instrumentos del reel 1 (video/audio/build_audio.py). Todo es determinista.
Salidas: video2/audio/out/mix_h1.wav, mix_h2.wav, mix_h3.wav (−14 LUFS) y music.wav.
Uso: python3 video2/audio/build_audio.py
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
spec.loader.exec_module(S)  # instrumentos: kick, hat, clap, pluck, bass_note, pad, riser, whoosh, impact…

SR = S.SR
TL = json.loads((ROOT / "video2/timeline.json").read_text())
WORDS = json.loads((HERE / "vo/words.json").read_text())
DUR = TL["duracion"]
N = int(DUR * SR)
BEAT = 60 / TL["bpm"]
LN = TL["lineas"]
SFX = ROOT / ".agents/skills/brag/assets/sfx"
OUT = HERE / "out"


def wt(line, word, n=0):
    """Segundo absoluto en que se dice una palabra."""
    base = TL["hook_start"] if line.startswith("h") else LN[line]
    hits = [w for w in WORDS[line]["words"] if w["w"].lower() == word.lower()]
    return base + hits[n]["t"]


def note(n):
    return S.note(n)


def build_music():
    L = np.zeros(N)
    R = np.zeros(N)

    def both(sig, at, g=1.0, pan=0.0):
        S.place(L, sig, at, g * (1 - max(pan, 0)))
        S.place(R, sig, at, g * (1 + min(pan, 0)))

    t_giro, t_rem, t_cta = TL["escenas"]["giro"], TL["escenas"]["remate"], TL["escenas"]["cta"]
    caps = [TL["escenas"]["cap1"], TL["escenas"]["cap2"], TL["escenas"]["cap3"]]
    t_sistema = wt("b5", "es", 1)  # el segundo "es": "Es el sistema"

    # GANCHO 0–3.4: drone grave + ticks + riser
    both(S.pad([note("D2"), note("A2"), note("D#3")], t_giro + 0.3, 700), 0, 0.5)
    for k in range(int(t_giro / (BEAT / 2))):
        both(S.hat() * 0.7, k * BEAT / 2, 0.22, pan=0.4 if k % 2 else -0.4)
    both(S.riser(1.6), t_giro - 1.6, 0.4)

    # GROOVE (3.4 → remate) en Re menor: Dm – Bb – F – C, beat partido tipo trap
    prog = [("D", ["D3", "F3", "A3"]), ("A#", ["A#2", "D3", "F3"]), ("F", ["F3", "A3", "C4"]), ("C", ["C3", "E3", "G3"])]
    roots = {"D": "D1", "A#": "A#0", "F": "F1", "C": "C1"}
    bar = BEAT * 4
    end_groove = t_rem  # "No es más presupuesto." queda casi en silencio
    side = np.ones(N)
    b0 = t_giro
    bi = 0
    while b0 < end_groove:
        root, chord = prog[bi % 4]
        bright = 1.0 if caps[1] <= b0 < caps[2] else 0.0  # capítulo 2 (claro) más brillante
        both(S.pad([note(n) for n in chord], bar + 0.3, 1600 + 1600 * bright), b0, 0.42)
        for s in range(16):
            ts = b0 + s * BEAT / 4
            if ts >= end_groove:
                break
            if s in (0, 10):
                both(S.kick(), ts, 0.95)
                i = int(ts * SR)
                d = np.minimum(S.t_axis(BEAT) / 0.15, 1.0) * 0.6 + 0.4
                side[i : i + len(d)] = np.minimum(side[i : i + len(d)], d[: len(side[i : i + len(d)])])
            if s == 8:
                both(S.clap(), ts, 0.5)
            both(S.hat(open_=(s == 14)), ts, 0.12 if s % 2 else 0.18, pan=0.3)
            if s in (0, 3, 6, 10, 12):
                both(S.bass_note(note(roots[root]), BEAT * 0.7), ts, 0.55)
            if bright and s % 2 == 0:
                both(S.pluck(note(chord[(s // 2) % 3]) * 2, 0.3, 5200), ts, 0.16, pan=-0.3 if s % 4 else 0.3)
        b0 += bar
        bi += 1
    i0, i1 = int(t_giro * SR), int(end_groove * SR)
    L[i0:i1] *= side[i0:i1]
    R[i0:i1] *= side[i0:i1]

    # golpes de estructura
    both(S.impact(1.4) * 0.8, t_giro, 0.8)
    for c in caps:
        both(S.impact(1.2) * 0.45, c, 0.6)
    # REMATE: "No es más presupuesto." queda casi en silencio → "Es el sistema." golpea
    both(S.pad([note("D2"), note("A2")], t_sistema - t_rem, 500), t_rem, 0.4)
    both(S.riser(t_sistema - t_rem), t_rem, 0.35)
    both(S.impact(2.0), t_sistema, 1.0)

    # CTA: resolución en Fa mayor con pulso suave hasta el final
    tail = DUR - t_sistema
    both(S.pad([note("F2"), note("C3"), note("F3"), note("A3"), note("C4")], tail, 2400), t_sistema, 0.7)
    for k in range(int(tail / BEAT)):
        ts = t_sistema + 0.6 + k * BEAT
        both(S.kick() * 0.6, ts, 0.55)
        both(S.hat(), ts + BEAT / 2, 0.12)
        both(S.bass_note(note("F1"), BEAT * 0.8), ts, 0.4)
    for k, n in enumerate(["F4", "A4", "C5", "F5"]):
        both(S.pluck(note(n), 0.8, 5000), t_cta + 0.3 + k * BEAT / 2, 0.14, pan=0.4 if k % 2 else -0.4)

    music = np.stack([S.reverb(L, 1.4, 0.15), S.reverb(R, 1.5, 0.15)], axis=1)
    fade = np.minimum((DUR - S.t_axis(DUR)) / 1.2, 1.0)[:, None]
    music *= fade
    return music / np.max(np.abs(music)) * 0.8


def sfx_list(hook):
    hook_hit = {"h1": wt("h1", "compran"), "h2": wt("h2", "desaparezcan"), "h3": wt("h3", "curiosos")}[hook]
    s = [
        ("ui/click3.ogg", 0.35, -14), ("ui/click5.ogg", 0.8, -15), ("ui/click2.ogg", 1.25, -15),
        ("impact/impactPunch_heavy_002.ogg", hook_hit, -6),
        ("interface/glitch_002.ogg", TL["escenas"]["giro"], -8), ("interface/glitch_004.ogg", TL["escenas"]["giro"] + 0.25, -12),
        ("interface/switch_005.ogg", wt("b1", "tres"), -12),
        # capítulo 1
        ("synth:whoosh", TL["escenas"]["cap1"] - 0.3, -10),
        ("ui/mouseclick1.ogg", wt("b2", "clics"), -8),
        ("impact/impactPunch_medium_001.ogg", wt("b2", "clic"), -9),
        ("ui/mouseclick1.ogg", wt("b2", "compra"), -8), ("interface/select_008.ogg", wt("b2", "compra") + 0.05, -12),
        # capítulo 2
        ("synth:whoosh", TL["escenas"]["cap2"] - 0.3, -10),
        ("interface/error_005.ogg", wt("b3", "quién"), -14), ("interface/error_005.ogg", wt("b3", "sigue"), -14),
        ("interface/drop_001.ogg", wt("b3", "preguntan"), -14), ("interface/drop_002.ogg", wt("b3", "preguntan") + 0.17, -14),
        ("interface/drop_003.ogg", wt("b3", "preguntan") + 0.33, -14), ("interface/switch_002.ogg", wt("b3", "cosa") + 0.47, -12),
        # capítulo 3
        ("synth:whoosh", TL["escenas"]["cap3"] - 0.3, -10),
        ("ui/click1.ogg", wt("b4", "nadie") - 0.2, -15), ("ui/click1.ogg", wt("b4", "nadie") - 0.03, -15), ("ui/click1.ogg", wt("b4", "nadie") + 0.13, -15),
        ("interface/switch_002.ogg", wt("b4", "atiende"), -11), ("interface/switch_002.ogg", wt("b4", "califica"), -11),
        ("interface/switch_002.ogg", wt("b4", "deriva"), -11),
        # cierre
        ("synth:whoosh", TL["escenas"]["cta"] - 0.35, -10), ("interface/bong_001.ogg", TL["escenas"]["cta"] + 0.5, -14),
    ]
    return s


def build_sfx(hook):
    buf = np.zeros((N, 2))
    for f, t, g in sfx_list(hook):
        sig = np.stack([S.whoosh()] * 2, axis=1) * 0.6 if f == "synth:whoosh" else S.load_audio(SFX / f)
        i = int(t * SR)
        j = min(N, i + len(sig))
        buf[i:j] += sig[: j - i] * S.db(g)
    return buf


def build_vo(hook):
    buf = np.zeros((N, 2))
    for lid, start in [(hook, TL["hook_start"])] + list(LN.items()):
        sig, sr = sf.read(HERE / "vo" / f"{lid}.wav")
        sig = S.hp(sig, 90)
        i = int(start * SR)
        j = min(N, i + len(sig))
        buf[i:j] += sig[: j - i, None]
    return buf


def main():
    OUT.mkdir(exist_ok=True)
    music = build_music()
    sf.write(OUT / "music.wav", music, SR, subtype="PCM_24")
    for hook in ("h1", "h2", "h3"):
        vo = build_vo(hook)
        vo = vo / np.max(np.abs(vo)) * 0.9
        mix = vo + music * S.duck_curve(vo) * 0.55 + build_sfx(hook) * 0.8
        mix = np.tanh(mix * 1.1) / np.tanh(1.1)
        raw = OUT / f"mix_{hook}_raw.wav"
        sf.write(raw, mix, SR, subtype="PCM_24")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.0:LRA=9",
                        "-ar", str(SR), "-c:a", "pcm_s24le", str(OUT / f"mix_{hook}.wav")], check=True)
        print("ok:", OUT / f"mix_{hook}.wav")


if __name__ == "__main__":
    main()

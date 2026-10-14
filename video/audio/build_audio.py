"""Banda sonora del reel MC Growth: música original + efectos + voz, mezclados.

Todo es determinista (semilla fija). Salidas en video/audio/out/:
  music.wav  — música sola
  mix.wav    — mezcla final (voz + música con ducking + efectos), -14 LUFS
Uso:  python3 video/audio/build_audio.py
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SFX_DIR = HERE.parents[1] / ".agents/skills/brag/assets/sfx"  # SFX de Brag (Kenney, CC0)
CUES = json.loads((HERE / "cues.json").read_text())
DUR = CUES["duracion"]
N = int(DUR * SR)
BEAT = 60 / CUES["bpm"]
M = CUES["momentos"]
rng = np.random.default_rng(482)


# ── utilidades ───────────────────────────────────────────────
def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[pitch] + (octave - 4) * 12) / 12)


def lp(x, hz, order=2):
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(freq, sec, detune=0.0):
    t = t_axis(sec)
    ph = (t * freq * (1 + detune)) % 1.0
    return 2 * ph - 1


def place(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def env_ad(sec, a, d):
    t = t_axis(sec)
    return np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-np.maximum(t - a, 0) / d)


def reverb(x, sec=2.2, mix=0.25):
    ir_t = t_axis(sec)
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / (sec / 5))
    ir = lp(ir, 6000)
    ir /= np.sqrt(np.sum(ir**2))
    wet = fftconvolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix


def db(g):
    return 10 ** (g / 20)


# ── instrumentos ─────────────────────────────────────────────
def kick():
    t = t_axis(0.5)
    f = 45 + 95 * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)
    click = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.004) * 0.3
    return np.tanh((body + click) * 1.6)


def hat(open_=False):
    sec = 0.25 if open_ else 0.05
    t = t_axis(sec)
    return hp(rng.standard_normal(len(t)), 7000, 4) * np.exp(-t / (0.07 if open_ else 0.012))


def clap():
    t = t_axis(0.3)
    n = bp(rng.standard_normal(len(t)), 900, 3500)
    e = sum(np.exp(-np.maximum(t - d, 0) / 0.01) * (t >= d) for d in (0, 0.011, 0.022)) + np.exp(-t / 0.09) * 0.6
    return n * e * 0.8


def pluck(freq, sec=0.35, bright=4500):
    s = saw(freq, sec) + saw(freq, sec, 0.004)
    return lp(s * env_ad(sec, 0.002, 0.11), bright) * 0.5


def bass_note(freq, sec):
    s = saw(freq, sec) * 0.6 + np.sin(2 * np.pi * freq * t_axis(sec)) * 0.8
    e = np.minimum(t_axis(sec) / 0.005, 1) * np.minimum((sec - t_axis(sec)) / 0.02, 1)
    return np.tanh(lp(s, 420) * 1.8) * e


def pad(freqs, sec, cutoff=1800):
    s = sum(saw(f, sec, d) for f in freqs for d in (-0.006, 0.0, 0.007))
    t = t_axis(sec)
    e = np.minimum(t / 0.6, 1) * np.minimum((sec - t) / 0.8, 1)
    return lp(s, cutoff) * e / (len(freqs) * 3)


def riser(sec):
    t = t_axis(sec)
    p = t / sec
    noise = rng.standard_normal(len(t))
    # barrido de filtro por bloques (de oscuro a brillante)
    out = np.zeros_like(noise)
    blk = 2400
    for i in range(0, len(t), blk):
        c = 300 + (9000 - 300) * p[i] ** 2
        out[i : i + blk] = bp(noise[i : i + blk + 0], max(150, c * 0.5), min(c * 1.5, 20000))[: len(out[i : i + blk])]
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * p**2) / SR) * 0.15
    return (out * 0.6 + tone) * p**1.6


def whoosh(sec=0.55):
    t = t_axis(sec)
    p = t / sec
    noise = rng.standard_normal(len(t))
    out = np.zeros_like(noise)
    blk = 1200
    for i in range(0, len(t), blk):
        c = 400 + 5000 * np.sin(np.pi * p[i]) ** 2
        out[i : i + blk] = bp(noise[i : i + blk], c * 0.6, min(c * 1.6, 20000))
    return out * np.sin(np.pi * p) ** 2


def impact(sec=2.4):
    t = t_axis(sec)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 40 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.9)
    crack = lp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.05) * 0.5
    return reverb(np.tanh((boom + crack) * 1.4), 2.6, 0.35)


# ── composición ──────────────────────────────────────────────
def build_music():
    L = np.zeros(N)
    R = np.zeros(N)

    def both(sig, at, g=1.0, pan=0.0):
        place(L, sig, at, g * (1 - max(pan, 0)))
        place(R, sig, at, g * (1 + min(pan, 0)))

    t_ord = M["orden"]  # 6.0 — del caos al orden
    t_cut = M["mas_ventas"]  # 2.0 — golpe "¿MÁS VENTAS?"
    t_vista = M["vista_total"]
    t_logo = M["logo"]

    # 1) CAOS 0–2.0: pulso nervioso, clúster disonante, ticks desparejos
    both(pad([note("A2"), note("A#2"), note("E3")], t_cut + 0.3, 900), 0, 0.55)
    for k in range(8):
        both(bass_note(note("A1"), 0.12), k * BEAT / 2, 0.55)
    ticks = np.sort(rng.uniform(0.05, t_cut - 0.1, 14))
    for i, tt in enumerate(ticks):
        both(hat() * 0.8, tt, 0.35, pan=0.6 if i % 2 else -0.6)
    both(riser(1.0), t_cut - 1.0, 0.35)
    both(impact(), t_cut, 0.9)

    # 2) PROBLEMA 2.0–6.0: latido sub + drone, riser hacia el cambio
    both(pad([note("A1"), note("E2")], t_ord - t_cut, 500), t_cut, 0.6)
    for b in np.arange(3.0, t_ord - 0.4, BEAT * 2):
        both(kick() * 0.7, b, 0.55)
    both(riser(1.4), t_ord - 1.4, 0.55)

    # 3) ORDEN 6.0–15.6: groove completo Am–F–C–G
    prog = [("A", ["A3", "C4", "E4"]), ("F", ["F3", "A3", "C4"]), ("C", ["C4", "E4", "G4"]), ("G", ["G3", "B3", "D4"]), ("A", ["A3", "C4", "E4"])]
    bass_roots = {"A": "A1", "F": "F1", "C": "C2", "G": "G1"}
    bar = BEAT * 4
    sidechain = np.ones(N)
    for bi in range(int(np.ceil((t_vista - t_ord) / bar))):
        b0 = t_ord + bi * bar
        root, chord = prog[bi % len(prog)]
        both(pad([note(n) for n in chord], bar + 0.4, 2400), b0, 0.5)
        for s in range(16):
            ts = b0 + s * BEAT / 4
            if ts >= t_vista - 0.05:
                break
            if s % 4 == 0:
                both(kick(), ts, 0.95)
                i = int(ts * SR)
                d = np.minimum(t_axis(BEAT) / 0.16, 1.0) * 0.65 + 0.35
                sidechain[i : i + len(d)] = np.minimum(sidechain[i : i + len(d)], d[: len(sidechain[i : i + len(d)])])
            if s % 8 == 4:
                both(clap(), ts, 0.45)
            both(hat(open_=(s % 4 == 2)), ts, 0.16 if s % 2 else 0.1, pan=0.35)
            if s % 2 == 0:
                both(bass_note(note(bass_roots[root]) * (2 if s % 8 == 6 else 1), BEAT / 2 - 0.02), ts, 0.5)
            arp = chord[[0, 1, 2, 1][s % 4]]
            f_arp = note(arp) * (2 if (s // 4) % 2 else 1)
            both(pluck(f_arp, 0.3, 3000 + 2500 * (bi / 5)), ts, 0.22, pan=-0.3 if s % 2 else 0.3)
    # el sidechain solo actúa sobre la sección del groove
    i0, i1 = int(t_ord * SR), int(t_vista * SR)
    L[i0:i1] *= sidechain[i0:i1]
    R[i0:i1] *= sidechain[i0:i1]
    both(impact(1.6) * 0.6, t_ord, 0.7)

    # 4) VISTA TOTAL 15.6–17.4: se abre, pad mayor y riser al logo
    both(pad([note("F3"), note("A3"), note("C4"), note("E4")], t_logo - t_vista + 0.5, 3200), t_vista, 0.75)
    both(bass_note(note("F1"), t_logo - t_vista), t_vista, 0.45)
    both(riser(t_logo - t_vista), t_vista, 0.5)

    # 5) LOGO 17.4–20: resolución en Do mayor + golpe + cola
    tail = DUR - t_logo
    both(impact(2.6), t_logo, 1.0)
    both(pad([note("C3"), note("G3"), note("C4"), note("E4"), note("G4")], tail, 2600), t_logo, 0.8)
    both(bass_note(note("C2"), tail - 0.4) * np.exp(-t_axis(tail - 0.4) / 1.4), t_logo, 0.55)
    for k, n in enumerate(["C5", "G4", "E5", "C6"]):
        both(pluck(note(n), 0.8, 5000), t_logo + 0.25 + k * BEAT / 2, 0.16, pan=0.4 if k % 2 else -0.4)

    music = np.stack([L, R], axis=1)
    music = np.stack([reverb(music[:, 0], 1.6, 0.18), reverb(music[:, 1], 1.7, 0.18)], axis=1)
    # salida suave al final
    fade = np.minimum((DUR - t_axis(DUR)) / 0.6, 1.0)[:, None]
    music *= fade
    return music / np.max(np.abs(music)) * 0.8


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def build_sfx():
    buf = np.zeros((N, 2))
    for c in CUES["sfx"]:
        sig = np.stack([whoosh()] * 2, axis=1) * 0.6 if c["file"] == "synth:whoosh" else load_audio(SFX_DIR / c["file"])
        i = int(c["t"] * SR)
        j = min(N, i + len(sig))
        buf[i:j] += sig[: j - i] * db(c["gain"])
    return buf


def build_vo():
    buf = np.zeros((N, 2))
    for v in CUES["vo"]:
        sig, sr = sf.read(HERE / "vo" / f"{v['id']}.wav")
        assert sr == SR
        sig = hp(sig, 90)
        i = int(v["start"] * SR)
        j = min(N, i + len(sig))
        buf[i:j, 0] += sig[: j - i]
        buf[i:j, 1] += sig[: j - i]
    return buf


def duck_curve(vo):
    # Baja la música mientras habla la voz (−9 dB), con ataque y release suaves
    lvl = np.abs(vo[:, 0])
    win = int(0.05 * SR)
    rms = np.sqrt(np.convolve(lvl**2, np.ones(win) / win, mode="same"))
    active = (rms > 0.01).astype(float)
    hold = int(0.25 * SR)
    active = np.convolve(active, np.ones(hold), mode="same") > 0
    target = np.where(active, db(-9), 1.0)
    smooth = np.convolve(target, np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
    return smooth[:, None]


def main():
    OUT.mkdir(exist_ok=True)
    music = build_music()
    sf.write(OUT / "music.wav", music, SR, subtype="PCM_24")
    vo = build_vo()
    vo = vo / np.max(np.abs(vo)) * 0.9
    sfx = build_sfx()
    mix = vo * 1.0 + music * duck_curve(vo) * 0.55 + sfx * 0.8
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # limitador suave
    sf.write(OUT / "mix_raw.wav", mix, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(OUT / "mix_raw.wav"),
                    "-af", "loudnorm=I=-14:TP=-1.0:LRA=9", "-ar", str(SR), "-c:a", "pcm_s24le", str(OUT / "mix.wav")], check=True)
    print("ok:", OUT / "mix.wav")


if __name__ == "__main__":
    main()

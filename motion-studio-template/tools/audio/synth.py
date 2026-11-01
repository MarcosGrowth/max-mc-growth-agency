"""Sintetizador de música y efectos para reels (determinista, sin samples con licencia).

Instrumentos: kick, hat, clap, pluck, bass_note, pad, riser, whoosh, impact; utilidades de filtros,
reverb, colocación en el tiempo, ducking de la música bajo la voz y mezcla final a −14 LUFS.
Se importa desde el build_audio.py de cada proyecto (ver plantillas/build_audio_ejemplo.py).
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
SFX_DIR = Path(__file__).resolve().parents[2] / ".claude/skills/brag/assets/sfx"  # efectos CC0 (Kenney) que trae Brag
rng = np.random.default_rng(482)

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
def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


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


def loudnorm(src, dst, lufs=-14):
    """Normaliza la mezcla a −14 LUFS con pico verdadero −1 dB (estándar de Reels)."""
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-af", f"loudnorm=I={lufs}:TP=-1.0:LRA=9",
                    "-ar", str(SR), "-c:a", "pcm_s24le", str(dst)], check=True)

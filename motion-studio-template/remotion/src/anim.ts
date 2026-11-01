import { Easing, interpolate } from "remotion";

// Progreso 0→1 entre dos frames, con curva de salida fuerte (entra rápido, asienta suave)
export const prog = (frame: number, start: number, dur: number, ease = Easing.bezier(0.16, 1, 0.3, 1)) =>
  interpolate(frame, [start, start + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

export const mix = (a: number, b: number, t: number) => a + (b - a) * t;

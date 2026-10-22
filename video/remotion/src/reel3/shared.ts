// Utilidades del reel 3: tiempos de palabras, azar determinista y geometría compartida con Hyperframes
import words from "../data/reel3_words.json";

export const FPS = 30;
type Line = { words: { w: string; t: number }[] };
const W = words as unknown as Record<string, Line>;
export const tw = (line: string, word: string, n = 0) => {
  const hits = W[line].words.filter((x) => x.w.toLowerCase() === word.toLowerCase());
  if (!hits[n]) throw new Error(`palabra no encontrada: ${line}/${word}`);
  return hits[n].t;
};

export function mulberry32(a: number) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Tarjeta del anuncio en la escena de rebote (misma caja que usa la composición de Hyperframes)
export const CARD = { x: 300, y: 400, w: 480, h: 520 };

// Utilidades del reel 2: tiempos de palabras de la voz y piezas comunes (cursor, sellos, etiquetas)
import React from "react";
import words from "../data/reel2_words.json";
import { C, MONO, SANS } from "../brand";
import { mix, prog } from "../anim";

export const FPS = 30;
export const RED = "#FF4D4D";

type Line = { words: { w: string; t: number }[] };
const W = words as unknown as Record<string, Line>;

// Segundo (relativo al inicio de la línea) en que se dice una palabra; n = ocurrencia (0 = primera)
export const tw = (line: string, word: string, n = 0) => {
  const hits = W[line].words.filter((x) => x.w.toLowerCase() === word.toLowerCase());
  if (!hits[n]) throw new Error(`palabra no encontrada: ${line}/${word}`);
  return hits[n].t;
};
export const fr = (sec: number) => Math.round(sec * FPS);

export const Cursor: React.FC<{ x: number; y: number; press: number; opacity: number }> = ({ x, y, press, opacity }) => (
  <svg width="54" height="64" viewBox="0 0 27 32" style={{ position: "absolute", left: x, top: y, opacity, transform: `scale(${1 - 0.15 * press})`, transformOrigin: "4px 4px", filter: "drop-shadow(0 6px 12px rgba(0,0,0,0.45))" }}>
    <path d="M2 2 L2 26 L8.5 20 L13 30 L17.5 28 L13 18.5 L22 18.5 Z" fill="#fff" stroke="#09090B" strokeWidth="2" strokeLinejoin="round" />
  </svg>
);

export const Tag: React.FC<{ text: string; color: string; t: number; style?: React.CSSProperties; dark?: boolean }> = ({ text, color, t, style, dark }) => (
  <div style={{ position: "absolute", fontFamily: MONO, fontSize: 24, letterSpacing: 2, fontWeight: 600, color: dark ? "#09090B" : color, background: dark ? color : `${color}22`,
    border: `2px solid ${color}`, padding: "10px 18px", borderRadius: 40, whiteSpace: "nowrap", opacity: t, transform: `scale(${mix(0.7, 1, t)})`, ...style }}>{text}</div>
);

export const Stamp: React.FC<{ text: string; t: number; color?: string; style?: React.CSSProperties }> = ({ text, t, color = RED, style }) => (
  <div style={{ position: "absolute", fontFamily: SANS, fontWeight: 900, fontSize: 64, letterSpacing: -1, color, border: `6px solid ${color}`, borderRadius: 18,
    padding: "6px 26px", whiteSpace: "nowrap", background: "rgba(9,9,11,0.55)", opacity: Math.min(1, t * 1.5), transform: `rotate(-8deg) scale(${mix(1.8, 1, t)})`, ...style }}>{text}</div>
);

export { C, MONO, SANS, mix, prog };

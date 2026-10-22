// Reel 3 — el sistema entero: personas que caen por las 4 etapas; algunas se filtran, las que llegan llenan "ventas"
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, MONO, SANS, fontCss } from "../brand";
import { prog } from "../anim";
import { FPS, mulberry32, tw } from "./shared";

const L5 = 12.5 - 8.4; // la línea a5 empieza 4.1 s después del inicio de este clip
const ETAPAS = [
  { n: "TE VEN", s: "Meta Ads + Google Ads", w0: 900, w1: 780, at: () => L5 + tw("a5", "ven") },
  { n: "CONSULTAN", s: "Landing", w0: 760, w1: 640, at: () => L5 + tw("a5", "ven") + 0.25 },
  { n: "MAX AI CALIFICA", s: "Inteligencia artificial", w0: 620, w1: 500, at: () => L5 + tw("a5", "hasta") },
  { n: "TE COMPRAN", s: "CRM + seguimiento", w0: 480, w1: 360, at: () => L5 + tw("a5", "compran") },
];
const TOP = 380, BAND = 120, GAP = 22, CX = 540;
const bandY = (i: number) => TOP + i * (BAND + GAP);
const BOTTOM = bandY(3) + BAND;
const BAR_Y = BOTTOM + 60;

// ancho del embudo a una altura y (para mantener a las personas adentro)
const widthAt = (y: number) => {
  for (let i = 0; i < 4; i++) {
    const a = bandY(i), b = a + BAND + GAP;
    if (y < b) return ETAPAS[i].w0 + (ETAPAS[i].w1 - ETAPAS[i].w0) * Math.max(0, Math.min(1, (y - a) / BAND));
  }
  return 340;
};

const rnd = mulberry32(517);
const N = 70;
const dots = Array.from({ length: N }, (_, i) => {
  const drop = rnd(); // en qué etapa se filtra (o si llega)
  const dropAt = drop < 0.25 ? 0 : drop < 0.45 ? 1 : drop < 0.62 ? 2 : -1;
  return { t0: 0.5 + i * 0.1 + rnd() * 0.1, xr: rnd() * 2 - 1, v: 430 + rnd() * 120, dropAt, dir: rnd() < 0.5 ? -1 : 1, r: 7 + rnd() * 4 };
});
const arrivals = dots.filter((d) => d.dropAt < 0).map((d) => d.t0 + (BAR_Y - 300) / d.v).sort((a, b) => a - b);

export const Embudo3: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / FPS;
  const arrived = arrivals.filter((a) => a <= t).length;
  const fill = arrived / arrivals.length;
  return (
    <AbsoluteFill>
      <style>{fontCss}</style>
      {ETAPAS.map((e, i) => {
        const appear = prog(f, 4 + i * 4, 14);
        const lit = prog(f, Math.round(e.at() * FPS), 8);
        const last = i === 3;
        return (
          <div key={e.n} style={{ position: "absolute", left: CX - e.w0 / 2, top: bandY(i), width: e.w0, height: BAND, opacity: appear,
            transform: `translateY(${(1 - appear) * 30}px)`,
            clipPath: `polygon(0 0, 100% 0, ${50 + (e.w1 / e.w0) * 50}% 100%, ${50 - (e.w1 / e.w0) * 50}% 100%)`,
            background: last ? `rgba(244,123,32,${0.25 + 0.6 * lit})` : `rgba(${23 + 20 * lit},${24 + 10 * lit},${29},0.96)`,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <div style={{ fontFamily: MONO, fontSize: 30, letterSpacing: 3, fontWeight: 600, color: last ? "#fff" : lit > 0.5 ? C.orange : "#AEB4C3" }}>{e.n}</div>
            <div style={{ fontFamily: SANS, fontSize: 27, fontWeight: 600, color: last ? "#FFF3E8" : "#8A90A0", marginTop: 4 }}>{e.s}</div>
          </div>
        );
      })}
      <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0 }}>
        {dots.map((d, i) => {
          const u = t - d.t0;
          if (u < 0) return null;
          let y = 300 + d.v * u;
          let x = CX + d.xr * (widthAt(Math.max(y, TOP)) / 2 - 40);
          let o = 1;
          if (d.dropAt >= 0) {
            const yd = bandY(d.dropAt) + BAND * 0.6;
            if (y > yd) {
              const v = (y - yd) / d.v;
              y = yd + 30 * v;
              x = CX + d.xr * (widthAt(yd) / 2 - 40) + d.dir * 700 * v;
              o = Math.max(0, 1 - v * 2.2);
            }
          } else if (y > BAR_Y) return null;
          return <circle key={i} cx={x} cy={y} r={d.r} fill={d.dropAt < 0 && y > bandY(3) ? C.orange : "#F5F6F8"} opacity={o * 0.92} />;
        })}
      </svg>
      {/* barra de ventas: se llena con las personas que llegan (sin números) */}
      <div style={{ position: "absolute", left: 240, top: BAR_Y, width: 600, opacity: prog(f, 10, 12) }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 28, letterSpacing: 4, color: "#AEB4C3", marginBottom: 12 }}>
          <span>VENTAS</span>
        </div>
        <div style={{ height: 18, borderRadius: 9, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
          <div style={{ width: `${interpolate(fill, [0, 1], [0, 100])}%`, height: "100%", borderRadius: 9, background: C.orange, boxShadow: `0 0 18px ${C.orange}` }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

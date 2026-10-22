// Reel 3 — personas (puntos) que llegan al anuncio y rebotan sin entrar
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { CARD, FPS, mulberry32 } from "./shared";

const N = 46;
const rnd = mulberry32(2026);
const cx = CARD.x + CARD.w / 2, cy = CARD.y + CARD.h / 2;
// cada punto: nace en un borde, viaja hasta la tarjeta, rebota hacia afuera y se apaga
const dots = Array.from({ length: N }, (_, i) => {
  const ang = rnd() * Math.PI * 2;
  const start = { x: cx + Math.cos(ang) * 900, y: cy + Math.sin(ang) * 1000 };
  // punto de impacto sobre el borde de la tarjeta (con margen)
  const hx = Math.max(CARD.x - 14, Math.min(CARD.x + CARD.w + 14, cx + Math.cos(ang) * 400));
  const hy = Math.max(CARD.y - 14, Math.min(CARD.y + CARD.h + 14, cy + Math.sin(ang) * 400));
  const out = ang + (rnd() - 0.5) * 1.6;
  return { start, hit: { x: hx, y: hy }, out, t0: 0.1 + i * 0.055 + rnd() * 0.2, travel: 0.55 + rnd() * 0.3, r: 7 + rnd() * 5 };
});

export const Rebote: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  return (
    <AbsoluteFill>
      <svg width={1080} height={1920}>
        {dots.map((d, i) => {
          const u = (t - d.t0) / d.travel;
          if (u < 0) return null;
          let x: number, y: number, o = 1;
          if (u < 1) {
            const e = 1 - Math.pow(1 - u, 2);
            x = d.start.x + (d.hit.x - d.start.x) * e;
            y = d.start.y + (d.hit.y - d.start.y) * e;
          } else {
            const v = u - 1;
            const dist = 260 * (1 - Math.exp(-v * 2.2));
            x = d.hit.x + Math.cos(d.out) * dist;
            y = d.hit.y + Math.sin(d.out) * dist + 40 * v * v;
            o = Math.max(0, 1 - v * 0.6);
          }
          return <circle key={i} cx={x} cy={y} r={d.r} fill="#F5F6F8" opacity={o * 0.9} />;
        })}
      </svg>
    </AbsoluteFill>
  );
};

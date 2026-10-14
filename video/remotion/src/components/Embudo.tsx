// "Embudo de conversión" — recreación vertical de la interfaz real de growth.mcmarketingdig.com
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { z } from "zod";
import { C, MONO, SANS, fontCss } from "../brand";
import { mix, prog } from "../anim";

export const embudoSchema = z.object({
  titulo: z.string(),
  estado: z.string(),
  etapas: z.array(z.object({ etiqueta: z.string(), nombre: z.string(), fase: z.string(), estilo: z.enum(["claro", "ia", "verde", "oscuro"]) })),
});
type Props = z.infer<typeof embudoSchema>;

const NODE_H = 150;
const GAP = 84;
const STEP = 10; // frames que tarda el lead en pasar de una etapa a la siguiente
const TRAVEL_START = 10;

const nodeStyle = (estilo: string, lit: number): React.CSSProperties => {
  const base: React.CSSProperties = { height: NODE_H, borderRadius: 26, padding: "0 38px", display: "flex", flexDirection: "column", justifyContent: "center", boxSizing: "border-box", width: 734 };
  if (estilo === "ia") return { ...base, background: C.ink, border: `3px solid ${C.orange}`, boxShadow: `0 18px 60px rgba(244,123,32,${0.15 + 0.45 * lit})`, color: C.text };
  if (estilo === "verde") return { ...base, background: "#FFFFFF", border: `3px solid ${C.green}`, boxShadow: `0 12px 40px rgba(26,201,121,${0.1 + 0.3 * lit})`, color: C.ink };
  if (estilo === "oscuro") return { ...base, background: C.ink, border: "3px solid #000", boxShadow: `0 12px 40px rgba(0,0,0,${0.2 + 0.3 * lit})`, color: C.text };
  return { ...base, background: "#FFFFFF", border: "3px solid #E2E2E5", boxShadow: "0 10px 30px rgba(0,0,0,0.08)", color: C.ink };
};

export const Embudo: React.FC<Props> = ({ titulo, estado, etapas }) => {
  const f = useCurrentFrame();
  const cardIn = prog(f, 0, 12);
  const lineColor = (i: number) => (i === 0 ? "#C9C9CE" : i === 1 ? C.orange : C.green);
  const tokenPos = Math.min(etapas.length - 1, Math.max(0, (f - TRAVEL_START) / STEP)); // 0..n-1 continuo
  const stepY = NODE_H + GAP;

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <style>{fontCss}</style>
      <div style={{ width: 900, borderRadius: 40, padding: "44px 48px 56px", boxSizing: "border-box", background: C.light, boxShadow: "0 50px 140px rgba(0,0,0,0.55)", opacity: cardIn, transform: `translateY(${mix(80, 0, cardIn)}px) scale(${mix(0.94, 1, cardIn)})` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 44 }}>
          <span style={{ fontFamily: MONO, fontSize: 24, letterSpacing: 3, color: "#6E6E76" }}>{titulo}</span>
          <span style={{ fontFamily: MONO, fontSize: 22, color: "#0F9E5E", background: "rgba(26,201,121,0.14)", padding: "10px 20px", borderRadius: 30 }}>● {estado}</span>
        </div>
        <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: GAP, alignItems: "flex-start" }}>
          {/* conectores verticales */}
          {etapas.slice(0, -1).map((_, i) => {
            const fill = Math.min(1, Math.max(0, tokenPos - i));
            return (
              <div key={i} style={{ position: "absolute", left: 24, top: NODE_H / 2 + i * stepY, width: 6, height: stepY, background: "#DADADF", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: "100%", height: `${fill * 100}%`, background: lineColor(i) }} />
              </div>
            );
          })}
          {etapas.map((e, i) => {
            const appear = prog(f, 4 + i * 3, 10);
            const lit = Math.min(1, Math.max(0, tokenPos - i + 1));
            return (
              <div key={e.nombre} style={{ marginLeft: 70, opacity: appear, transform: `translateX(${mix(-40, 0, appear)}px)` }}>
                <div style={nodeStyle(e.estilo, lit)}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 22, letterSpacing: 2 }}>
                    <span style={{ opacity: 0.6 }}>{e.etiqueta}</span><span style={{ opacity: 0.45 }}>{e.fase}</span>
                  </div>
                  <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40, marginTop: 10 }}>{e.nombre}</div>
                </div>
              </div>
            );
          })}
          {/* el lead que recorre el sistema */}
          <div style={{ position: "absolute", left: 27 - 20, top: NODE_H / 2 - 20 + tokenPos * stepY, width: 40, height: 40, borderRadius: 20, background: C.orange, boxShadow: `0 0 0 10px rgba(244,123,32,0.18), 0 0 40px ${C.orange}`, opacity: prog(f, TRAVEL_START - 4, 4) }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

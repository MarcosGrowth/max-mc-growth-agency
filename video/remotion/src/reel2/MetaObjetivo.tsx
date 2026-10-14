// Capítulo 01 — "El objetivo": selector genérico de objetivo de campaña
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontCss } from "../brand";
import { C, Cursor, MONO, RED, SANS, Stamp, Tag, fr, mix, prog, tw } from "./shared";

const OPC = ["Reconocimiento", "Tráfico", "Interacción", "Clientes potenciales", "Promoción de la app", "Ventas"];
const PX = 110, PY = 400, ROW = 84, HEAD = 128;
const rowY = (i: number) => PY + HEAD + i * ROW;

export const MetaObjetivo: React.FC = () => {
  const f = useCurrentFrame();
  const L = "b2";
  const tClic = fr(tw(L, "clics")), tTrae = fr(tw(L, "trae")), tHace = fr(tw(L, "clic")), tNo = fr(tw(L, "No")), tCompra = fr(tw(L, "compra"));
  const panel = prog(f, 0, 12);
  // cursor: entra, va a "Tráfico", hace clic; luego salta a "Clientes potenciales"
  const p1 = prog(f, tClic - 22, 18), p2 = prog(f, tNo, 14);
  const cx = mix(mix(760, 230, p1), 230, p2), cy = mix(mix(1000, rowY(1) + 24, p1), rowY(3) + 24, p2);
  const press = Math.max(interpolate(f, [tClic - 2, tClic, tClic + 4], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
    interpolate(f, [tCompra - 2, tCompra, tCompra + 4], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const selTraf = f >= tClic && f < tCompra, selLead = f >= tCompra;
  const bad = prog(f, tHace, 8), badOut = prog(f, tCompra, 8), good = prog(f, tCompra, 10);

  return (
    <AbsoluteFill>
      <style>{fontCss}</style>
      <div style={{ position: "absolute", left: PX, top: PY, width: 860, height: HEAD + OPC.length * ROW + 20, borderRadius: 30, boxSizing: "border-box",
        background: "linear-gradient(180deg,#17181D,#0D0D10)", border: "1.5px solid rgba(255,255,255,0.1)", boxShadow: "0 40px 120px rgba(0,0,0,0.6)",
        opacity: panel, transform: `translateY(${mix(50, 0, panel)}px)` }}>
        <div style={{ padding: "30px 36px 0" }}>
          <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 3, color: "#8A90A0" }}>NUEVA CAMPAÑA</div>
          <div style={{ fontFamily: SANS, fontSize: 40, fontWeight: 800, color: C.text, marginTop: 8 }}>Objetivo de la campaña</div>
        </div>
      </div>
      {OPC.map((o, i) => {
        const on = (i === 1 && selTraf) || (i === 3 && selLead);
        const col = i === 3 && selLead ? C.green : i === 1 && f >= tHace && !selLead ? RED : "#F5F6F8";
        const appear = prog(f, 4 + i * 2, 10);
        return (
          <div key={o} style={{ position: "absolute", left: PX + 20, top: rowY(i), width: 820, height: ROW - 12, borderRadius: 18, boxSizing: "border-box",
            display: "flex", alignItems: "center", gap: 24, padding: "0 24px", opacity: panel * appear,
            background: on ? (i === 3 ? "rgba(26,201,121,0.12)" : "rgba(255,77,77,0.10)") : "transparent",
            border: `2px solid ${on ? col : "rgba(255,255,255,0.06)"}` }}>
            <div style={{ width: 30, height: 30, borderRadius: 15, border: `3px solid ${on ? col : "#5C6170"}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              {on ? <div style={{ width: 14, height: 14, borderRadius: 7, background: col }} /> : null}
            </div>
            <div style={{ fontFamily: SANS, fontSize: 34, fontWeight: on ? 800 : 500, color: on ? col : "#C9CDD6" }}>{o}</div>
          </div>
        );
      })}
      <Tag text="CLICS BARATOS" color={RED} t={prog(f, tClic + 4, 8) * (1 - badOut)} style={{ left: 560, top: rowY(1) + 12 }} />
      <Tag text="✓ LA QUE IMPORTA" color={C.green} t={good} style={{ left: 640, top: rowY(3) + 12 }} dark />
      <Stamp text="CLIC ≠ COMPRA" t={bad * (1 - badOut)} style={{ left: 300, top: rowY(4) + 6 }} />
      <Cursor x={cx} y={cy} press={press} opacity={prog(f, tClic - 26, 6)} />
      {/* destello de "gente que hace clic": punteros que aparecen y se van */}
      {[0, 1, 2, 3, 4].map((k) => {
        const s = tTrae + k * 3, a = interpolate(f, [s, s + 5, s + 16], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return <Cursor key={k} x={620 + k * 70} y={rowY(1) - 40 - (k % 2) * 40 - a * 20} press={0} opacity={a * 0.8} />;
      })}
    </AbsoluteFill>
  );
};

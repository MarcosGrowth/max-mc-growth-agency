// Capítulo 03 — "La respuesta": consultas sin responder que se enfrían → Max AI atiende, califica y deriva
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { fontCss } from "../brand";
import { C, MONO, SANS, fr, mix, prog, tw } from "./shared";

const ICE = "#8FB8DE";
const consultas = [
  { k: "INSTAGRAM", t: "Nueva consulta" },
  { k: "WHATSAPP", t: "Nueva consulta" },
  { k: "FORMULARIO", t: "Nueva consulta" },
];
const tareas = [
  { n: "01", t: "Atención inicial", w: "atiende" },
  { n: "02", t: "Calificación", w: "califica" },
  { n: "03", t: "Derivación", w: "deriva" },
];

export const MaxAITareas: React.FC = () => {
  const f = useCurrentFrame();
  const L = "b4";
  const tNadie = fr(tw(L, "nadie")), tEnfria = fr(tw(L, "consulta")), tMax = fr(tw(L, "Max"));
  const cold = prog(f, tEnfria, 30, (x) => x);
  const maxIn = prog(f, tMax - 4, 14);
  return (
    <AbsoluteFill>
      <style>{fontCss}</style>
      {/* consultas sin responder */}
      {consultas.map((c, i) => {
        const a = prog(f, tNadie - 6 + i * 5, 10);
        const away = maxIn;
        return (
          <div key={c.k} style={{ position: "absolute", left: 150 + i * 30, top: 420 + i * 150, width: 760, height: 124, borderRadius: 24, boxSizing: "border-box", padding: "20px 28px",
            background: `rgba(${mix(23, 30, cold)},${mix(24, 40, cold)},${mix(29, 56, cold)},0.96)`, border: `2px solid ${cold > 0.3 ? `rgba(143,184,222,${0.6 * cold})` : "rgba(255,255,255,0.1)"}`,
            boxShadow: "0 24px 60px rgba(0,0,0,0.5)", opacity: a * (1 - away * 0.85), filter: `saturate(${1 - cold * 0.7}) blur(${away * 4}px)`,
            transform: `translateY(${mix(40, 0, a) + away * 60}px) scale(${1 - away * 0.08})` }}>
            <div style={{ fontFamily: MONO, fontSize: 21, letterSpacing: 3, color: "#8A90A0" }}>{c.k}</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
              <span style={{ fontFamily: SANS, fontSize: 36, fontWeight: 700, color: C.text }}>{c.t}</span>
              <span style={{ fontFamily: MONO, fontSize: 21, letterSpacing: 2, padding: "8px 16px", borderRadius: 30,
                color: cold > 0.5 ? ICE : "#FFB36F", border: `2px solid ${cold > 0.5 ? ICE : "rgba(255,154,77,0.7)"}` }}>{cold > 0.5 ? "FRÍA" : "SIN RESPONDER"}</span>
            </div>
          </div>
        );
      })}
      {/* Max AI: la tarjeta del sitio con sus tres funciones */}
      <div style={{ position: "absolute", left: 110, top: 400, width: 860, borderRadius: 32, boxSizing: "border-box", padding: 36,
        background: "linear-gradient(180deg,#1B140F,#0D0D10)", border: "2px solid rgba(244,123,32,0.5)", boxShadow: `0 40px 120px rgba(0,0,0,0.6), 0 0 ${80 * maxIn}px rgba(244,123,32,0.3)`,
        opacity: maxIn, transform: `translateY(${mix(80, 0, maxIn)}px) scale(${mix(0.92, 1, maxIn)})` }}>
        <div style={{ display: "flex", gap: 28, alignItems: "center" }}>
          <div style={{ width: 110, height: 110, borderRadius: 28, border: `4px solid ${C.orange}`, display: "flex", alignItems: "center", justifyContent: "center", gap: 18, position: "relative", boxShadow: "0 0 30px rgba(244,123,32,0.4)" }}>
            <div style={{ width: 16, height: 16, borderRadius: 8, background: C.orange }} />
            <div style={{ width: 16, height: 16, borderRadius: 8, background: C.orange }} />
          </div>
          <div>
            <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 3, color: C.orange }}>AGENTE COMERCIAL</div>
            <div style={{ fontFamily: SANS, fontSize: 54, fontWeight: 800, color: C.text, marginTop: 4 }}>Max AI</div>
            <div style={{ fontFamily: SANS, fontSize: 26, color: "#AEB4C3", marginTop: 4 }}>Siempre activo. Siempre aprendiendo.</div>
          </div>
        </div>
        <div style={{ marginTop: 30, display: "flex", flexDirection: "column", gap: 16 }}>
          {tareas.map((t, i) => {
            const on = prog(f, fr(tw(L, t.w)), 8);
            const show = prog(f, tMax + 4 + i * 3, 10);
            return (
              <div key={t.n} style={{ display: "flex", alignItems: "center", gap: 22, padding: "20px 24px", borderRadius: 20, opacity: show,
                background: on > 0.5 ? "rgba(26,201,121,0.12)" : "rgba(255,255,255,0.03)", border: `2px solid ${on > 0.5 ? C.green : "rgba(255,255,255,0.08)"}` }}>
                <span style={{ fontFamily: MONO, fontSize: 26, color: C.orange }}>{t.n}</span>
                <span style={{ flex: 1, fontFamily: SANS, fontSize: 36, fontWeight: 700, color: C.text }}>{t.t}</span>
                <span style={{ width: 46, height: 46, borderRadius: 23, background: C.green, color: "#09090B", fontSize: 28, fontWeight: 900, fontFamily: SANS,
                  display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${on})` }}>✓</span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Capítulo 02 — "La landing": página genérica que no dice para quién es ni qué sigue → versión que filtra
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontCss } from "../brand";
import { C, MONO, RED, SANS, Tag, fr, mix, prog, tw } from "./shared";

const X = 110, Y = 400, Wd = 860;

export const Landing: React.FC = () => {
  const f = useCurrentFrame();
  const L = "b3";
  const tQuien = fr(tw(L, "quién")), tSigue = fr(tw(L, "sigue")), tPreg = fr(tw(L, "preguntan")), tFix = fr(tw(L, "cosa")) + 14;
  const card = prog(f, 0, 12);
  const fix = prog(f, tFix, 12);
  const bQ = prog(f, tQuien, 8) * (1 - fix), bS = prog(f, tSigue, 8) * (1 - fix);
  const bubbles = ["¿Qué hacen?", "¿Precio?", "¿Info?"];
  return (
    <AbsoluteFill>
      <style>{fontCss}</style>
      <div style={{ position: "absolute", left: X, top: Y, width: Wd, height: 600, borderRadius: 30, background: "#FFFFFF", overflow: "hidden",
        boxShadow: "0 40px 100px rgba(9,9,11,0.18), 0 0 0 1.5px #E3E3E8", opacity: card, transform: `translateY(${mix(50, 0, card)}px)` }}>
        <div style={{ height: 56, background: "#F2F2F4", display: "flex", alignItems: "center", gap: 12, padding: "0 24px", borderBottom: "1.5px solid #E3E3E8" }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
          <div style={{ marginLeft: 20, fontFamily: MONO, fontSize: 20, color: "#8A8A93", background: "#fff", padding: "6px 18px", borderRadius: 10 }}>tuempresa.com</div>
        </div>
        <div style={{ position: "relative", padding: "44px 48px" }}>
          {/* versión "antes" */}
          <div style={{ opacity: 1 - fix }}>
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 52, color: "#16161A", letterSpacing: -1.5, lineHeight: 1.05,
              outline: bQ > 0 ? `4px dashed rgba(255,77,77,${bQ})` : "none", outlineOffset: 10, borderRadius: 6 }}>Bienvenidos a nuestra web</div>
            <div style={{ fontFamily: SANS, fontSize: 28, color: "#7A7A84", marginTop: 20, lineHeight: 1.35 }}>Somos líderes en soluciones integrales para tu negocio.</div>
            <div style={{ display: "flex", gap: 16, marginTop: 30 }}>
              {[0, 1, 2].map((k) => <div key={k} style={{ flex: 1, height: 120, borderRadius: 16, background: "#EDEDF1" }} />)}
            </div>
            <div style={{ display: "inline-block", marginTop: 34, fontFamily: SANS, fontWeight: 700, fontSize: 30, color: "#fff", background: "#3A3A42", padding: "18px 34px", borderRadius: 14,
              outline: bS > 0 ? `4px dashed rgba(255,77,77,${bS})` : "none", outlineOffset: 8 }}>Contactanos</div>
          </div>
          {/* versión "después": dice para quién es y qué sigue */}
          <div style={{ position: "absolute", left: 48, right: 48, top: 44, opacity: fix, transform: `translateY(${mix(24, 0, fix)}px)` }}>
            <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 3, color: C.orange }}>PARA EMPRESAS QUE INVIERTEN EN PAUTA</div>
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 52, color: "#16161A", letterSpacing: -1.5, lineHeight: 1.05, marginTop: 14 }}>Convertí tu inversión en oportunidades.</div>
            <div style={{ display: "flex", gap: 14, marginTop: 30 }}>
              {["01 Diagnóstico", "02 Intervención", "03 Medición"].map((s) => (
                <div key={s} style={{ flex: 1, fontFamily: MONO, fontSize: 21, color: "#16161A", background: "#F4F4F6", border: "1.5px solid #E3E3E8", borderRadius: 14, padding: "18px 14px" }}>{s}</div>
              ))}
            </div>
            <div style={{ display: "inline-flex", gap: 14, marginTop: 34, fontFamily: SANS, fontWeight: 800, fontSize: 30, color: "#09090B", background: C.orange, padding: "18px 34px", borderRadius: 14 }}>Solicitar diagnóstico ↗</div>
          </div>
        </div>
      </div>
      <Tag text="¿PARA QUIÉN?" color={RED} t={bQ} style={{ left: 660, top: Y - 30 }} dark />
      <Tag text="¿QUÉ SIGUE?" color={RED} t={bS} style={{ left: 420, top: Y + 470 }} dark />
      <Tag text="✓ PARA QUIÉN" color={C.green} t={prog(f, tFix + 6, 8)} style={{ left: 620, top: Y - 30 }} dark />
      <Tag text="✓ QUÉ SIGUE" color={C.green} t={prog(f, tFix + 10, 8)} style={{ left: 640, top: Y + 560 }} dark />
      {bubbles.map((b, i) => {
        const s = tPreg + i * 5;
        const a = prog(f, s, 8) * (1 - fix);
        return (
          <div key={b} style={{ position: "absolute", left: 140 + i * 250, top: Y + 640 - (i % 2) * 30, fontFamily: SANS, fontSize: 32, fontWeight: 600, color: "#16161A",
            background: "#fff", border: "2px solid #E3E3E8", padding: "16px 24px", borderRadius: 24, borderBottomLeftRadius: 6, boxShadow: "0 16px 40px rgba(9,9,11,0.12)",
            opacity: a, transform: `translateY(${interpolate(a, [0, 1], [30, 0])}px) scale(${mix(0.8, 1, a)})` }}>{b}</div>
        );
      })}
    </AbsoluteFill>
  );
};

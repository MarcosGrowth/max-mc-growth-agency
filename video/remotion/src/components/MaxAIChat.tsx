// Tarjeta "MAX AI · LIVE" — recreación animada de la interfaz real de growth.mcmarketingdig.com
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { z } from "zod";
import { C, MONO, SANS, fontCss } from "../brand";
import { mix, prog } from "../anim";

export const maxAIChatSchema = z.object({
  leadId: z.string(),
  mensajes: z.array(z.object({ de: z.enum(["lead", "max"]), texto: z.string() })),
  metricas: z.array(z.object({ nombre: z.string(), valor: z.number() })),
  estadoFinal: z.string(),
});
type Props = z.infer<typeof maxAIChatSchema>;

const MSG_START = 4; // frame del primer mensaje
const MSG_GAP = 8; // frames entre mensajes

const Bubble: React.FC<{ de: "lead" | "max"; texto: string; t: number; typing: number }> = ({ de, texto, t, typing }) => {
  const isMax = de === "max";
  return (
    <div style={{ display: "flex", justifyContent: isMax ? "flex-end" : "flex-start", opacity: t, transform: `translateY(${mix(26, 0, t)}px) scale(${mix(0.96, 1, t)})`, transformOrigin: isMax ? "right bottom" : "left bottom" }}>
      <div style={{
        maxWidth: 640, padding: "20px 26px", borderRadius: 22,
        borderBottomRightRadius: isMax ? 6 : 22, borderBottomLeftRadius: isMax ? 22 : 6,
        background: isMax ? "rgba(244,123,32,0.10)" : C.surface2,
        border: `1.5px solid ${isMax ? "rgba(244,123,32,0.55)" : "rgba(255,255,255,0.08)"}`,
        color: isMax ? "#FFE3CC" : C.text, fontFamily: SANS, fontSize: 30, lineHeight: 1.32, fontWeight: 500,
      }}>
        {typing < 1 && isMax ? (
          <span style={{ display: "inline-flex", gap: 8 }}>
            {[0, 1, 2].map((i) => (
              <span key={i} style={{ width: 10, height: 10, borderRadius: 5, background: C.orangeLight, opacity: 0.35 + 0.65 * Math.abs(Math.sin((typing * 3 + i * 0.33) * Math.PI)) }} />
            ))}
          </span>
        ) : texto}
      </div>
    </div>
  );
};

export const MaxAIChat: React.FC<Props> = ({ leadId, mensajes, metricas, estadoFinal }) => {
  const f = useCurrentFrame();
  const panelIn = prog(f, 0, 12);
  const analysisStart = MSG_START + mensajes.length * MSG_GAP + 2;
  const aIn = prog(f, analysisStart, 10);
  const doneIn = prog(f, analysisStart + 18, 8);

  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", background: "transparent" }}>
      <style>{fontCss}</style>
      <div style={{
        width: 900, padding: 40, borderRadius: 36, boxSizing: "border-box",
        background: "linear-gradient(180deg, rgba(23,24,29,0.97), rgba(13,13,16,0.97))",
        border: "1.5px solid rgba(244,123,32,0.38)",
        boxShadow: `0 0 0 1px rgba(255,255,255,0.03), 0 40px 120px rgba(0,0,0,0.6), 0 0 ${mix(0, 90, panelIn)}px rgba(244,123,32,0.22)`,
        opacity: panelIn, transform: `translateY(${mix(60, 0, panelIn)}px)`,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontFamily: MONO, fontSize: 24, letterSpacing: 2, paddingBottom: 26, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
          <span style={{ color: C.gray, display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ width: 12, height: 12, borderRadius: 6, background: C.green, boxShadow: `0 0 14px ${C.green}` }} />MAX AI · LIVE
          </span>
          <span style={{ color: C.orange }}>{leadId}</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 18, padding: "30px 0" }}>
          {mensajes.map((m, i) => {
            const s = MSG_START + i * MSG_GAP;
            const typingDur = m.de === "max" ? 5 : 0;
            return <Bubble key={i} de={m.de} texto={m.texto} t={prog(f, s, 9)} typing={typingDur ? prog(f, s, typingDur, (x) => x) : 1} />;
          })}
        </div>

        <div style={{ borderRadius: 24, padding: 30, border: "1.5px solid rgba(26,201,121,0.35)", background: "rgba(26,201,121,0.06)", opacity: aIn, transform: `translateY(${mix(30, 0, aIn)}px)` }}>
          <div style={{ fontFamily: MONO, fontSize: 21, letterSpacing: 3, color: C.green }}>ANÁLISIS EN TIEMPO REAL</div>
          <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40, color: C.text, margin: "10px 0 22px" }}>Lead calificado</div>
          {metricas.map((m, i) => {
            const b = prog(f, analysisStart + 3 + i * 3, 12);
            return (
              <div key={m.nombre} style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 24, color: C.gray, marginBottom: 8 }}>
                  <span>{m.nombre}</span><span style={{ color: C.green }}>{Math.round(m.valor * b)}%</span>
                </div>
                <div style={{ height: 8, borderRadius: 4, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                  <div style={{ width: `${m.valor * b}%`, height: "100%", borderRadius: 4, background: C.green, boxShadow: `0 0 12px ${C.green}` }} />
                </div>
              </div>
            );
          })}
          <div style={{ marginTop: 18, padding: "16px 0", textAlign: "center", borderRadius: 14, border: "1.5px solid rgba(26,201,121,0.45)", background: "rgba(26,201,121,0.12)", fontFamily: MONO, fontSize: 23, color: "#BFF5DA", opacity: doneIn, transform: `scale(${mix(0.94, 1, doneIn)})` }}>
            ✓ {estadoFinal}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

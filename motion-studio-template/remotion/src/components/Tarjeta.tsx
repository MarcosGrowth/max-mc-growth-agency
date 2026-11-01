// Ejemplo de pieza de datos: tarjeta con una lista que se tilda. Se renderiza con fondo transparente
// y se inserta en la composición de Hyperframes como <video>.
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { z } from "zod";
import { C, DISPLAY, SANS, fontCss } from "../brand";
import { mix, prog } from "../anim";

export const tarjetaSchema = z.object({ titulo: z.string(), items: z.array(z.string()) });

export const Tarjeta: React.FC<z.infer<typeof tarjetaSchema>> = ({ titulo, items }) => {
  const f = useCurrentFrame();
  const t = prog(f, 0, 12);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <style>{fontCss}</style>
      <div style={{ width: 860, padding: 44, borderRadius: 32, background: C.surface, opacity: t, transform: `translateY(${mix(50, 0, t)}px)` }}>
        <div style={{ fontFamily: DISPLAY, fontSize: 52, fontWeight: 800, color: C.text }}>{titulo}</div>
        {items.map((it, i) => {
          const on = prog(f, 20 + i * 12, 8);
          return (
            <div key={it} style={{ display: "flex", gap: 20, alignItems: "center", marginTop: 20, fontFamily: SANS, fontSize: 36, color: C.text }}>
              <span style={{ width: 44, height: 44, borderRadius: 22, background: C.accent, transform: `scale(${on})`, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>✓</span>
              {it}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

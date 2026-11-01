// Tokens de la marca — completar con los valores de marca/marca.md
import { staticFile } from "remotion";

export const C = {
  bg: "#101010",
  surface: "#1B1B1F",
  text: "#F5F5F5",
  gray: "#A0A0A8",
  accent: "#3B82F6",
  ok: "#22C55E",
  error: "#EF4444",
};

// Copiar las tipografías de la marca a public/fonts/ con estos nombres
export const fontCss = `
@font-face { font-family: "Marca Display"; src: url("${staticFile("fonts/display.woff2")}") format("woff2"); font-weight: 100 900; }
@font-face { font-family: "Marca Texto"; src: url("${staticFile("fonts/texto.woff2")}") format("woff2"); font-weight: 100 900; }
`;
export const DISPLAY = '"Marca Display", Arial, sans-serif';
export const SANS = '"Marca Texto", Arial, sans-serif';

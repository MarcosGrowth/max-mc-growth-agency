// Tokens de marca tomados de growth.mcmarketingdig.com
import { staticFile } from "remotion";

export const C = {
  bg: "#09090B",
  surface: "#0D0D10",
  surface2: "#17181D",
  orange: "#F47B20",
  orangeLight: "#FF9A4D",
  orangeSoft: "#FFB36F",
  orangeDeep: "#7B2905",
  text: "#F5F6F8",
  gray: "#AEB4C3",
  grayDim: "#7C8291",
  green: "#1AC979",
  light: "#F2F2F3",
  ink: "#0B0B0D",
};

export const fontCss = `
@font-face { font-family: "Geist"; src: url("${staticFile("fonts/Geist-Variable.woff2")}") format("woff2"); font-weight: 100 900; }
@font-face { font-family: "Geist Mono"; src: url("${staticFile("fonts/GeistMono-Variable.woff2")}") format("woff2"); font-weight: 100 900; }
`;

export const SANS = '"Geist", Arial, sans-serif';
export const MONO = '"Geist Mono", monospace';

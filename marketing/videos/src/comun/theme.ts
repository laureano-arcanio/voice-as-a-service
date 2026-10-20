import { loadFont } from "@remotion/fonts";
import { Easing, staticFile } from "remotion";

// Tokens de la landing (landing/src/styles/global.css)
export const C = {
  bg: "#ffffff",
  bg2: "#f6f8fb",
  surface2: "#f1f4f9",
  ink: "#0b1220",
  ink2: "#33415c",
  muted: "#64748b",
  line: "#e3e8ef",
  line2: "#cbd5e1",
  accent: "#2456e6",
  accentSoft: "#eaf0ff",
  accent2: "#1740b8",
  accentOnDark: "#9db6ff",
  ok: "#1b9c5b",
  okSoft: "#e3f6ec",
  wa: "#13843f",
  warn: "#b42318",
  warnSoft: "#fef3f2",
  ctaInk: "#f4f6fa",
  ctaMuted: "#b8c2d6",
};

export const F = {
  display: "Bricolage Grotesque, sans-serif",
  body: "Figtree, sans-serif",
  mono: "IBM Plex Mono, monospace",
};

loadFont({ family: "Bricolage Grotesque", url: staticFile("fonts/bricolage-grotesque-latin-wght-normal.woff2"), weight: "200 800" });
loadFont({ family: "Figtree", url: staticFile("fonts/figtree-latin-wght-normal.woff2"), weight: "300 900" });
loadFont({ family: "IBM Plex Mono", url: staticFile("fonts/ibm-plex-mono-latin-500-normal.woff2"), weight: "500" });

export const shadowCard = "0 12px 34px rgba(11, 18, 32, 0.08)";
export const EASE = Easing.bezier(0.16, 1, 0.3, 1);
export const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

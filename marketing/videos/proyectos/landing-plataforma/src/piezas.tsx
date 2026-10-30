import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { AT, DUR, ESCENA_DE, SCENES, SUBS, type VoId } from "./timeline";

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

/** 0 → 1 entre a y a + d (s), y de vuelta a 0 desde b (s) si se pasa. */
export const win = (t: number, a: number, b = 999, d = 0.35) =>
  Math.min(interpolate(t, [a, a + d], [0, 1], CLAMP), interpolate(t, [b, b + d], [1, 0], CLAMP));

export type Retrato = "tomas" | "lucia" | "martina" | "valentina" | "lucas" | "sofia" | "martin" | "carolina" | "diego" | "jimena" | "gabriela" | "mateo" | "camila" | "mariana" | "federico" | "agustina";

/** Retrato de una voz (los mismos SVG del asistente de primera vez, web/public/voces/). */
export const Avatar: React.FC<{ id: Retrato; size: number; ring?: string; style?: React.CSSProperties; gray?: number }> = ({ id, size, ring, style, gray = 0 }) => (
  <div style={{
    width: size, height: size, borderRadius: "50%", boxShadow: ring ? `0 0 0 ${Math.max(4, size / 34)}px ${ring}` : "0 10px 28px rgba(11,18,32,0.14)",
    background: "#fff", flexShrink: 0, ...style,
  }}>
    <Img src={staticFile(`proyectos/landing-plataforma/voces/${id}.svg`)} style={{ width: size, height: size, borderRadius: "50%", filter: gray ? `grayscale(${gray})` : undefined }} />
  </div>
);

/** Lo que depende del plan: borde amarillo, como en el panel (DESIGN_GUIDELINE_APP, funciones por plan). */
export const PlanBadge: React.FC<{ children: React.ReactNode; p?: number; style?: React.CSSProperties }> = ({ children, p = 1, style }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 12, background: "#fff8e6", border: "2px solid #e8b931",
    borderRadius: 14, padding: "8px 16px", fontFamily: F.body, fontWeight: 600, fontSize: 22, color: "#7a5200",
    opacity: p, whiteSpace: "nowrap", ...style,
  }}>
    <span style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: "#a06c00" }}>PLAN</span>
    {children}
  </div>
);

export const Nota: React.FC<{ children: React.ReactNode; p?: number; style?: React.CSSProperties; color?: string }> = ({ children, p = 1, style, color = C.muted }) => (
  <div style={{ fontFamily: F.mono, fontSize: 18, color, opacity: p, letterSpacing: "0.02em", ...style }}>{children}</div>
);

/** Íconos propios que no están en ui.tsx. */
export const Glyph: React.FC<{ name: "music" | "db" | "x" | "ring" | "doc" | "key" | "chat" | "out"; size?: number; color?: string }> = ({ name, size = 28, color = "currentColor" }) => {
  const p = { fill: "none", stroke: color, strokeWidth: 2.2, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size}>
      {name === "music" ? (<><path {...p} d="M9 18V5l11-2v13" /><circle {...p} cx={6} cy={18} r={3} /><circle {...p} cx={17} cy={16} r={3} /></>) : null}
      {name === "db" ? (<><ellipse {...p} cx={12} cy={5.5} rx={8} ry={3} /><path {...p} d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>) : null}
      {name === "x" ? <path {...p} d="M6 6l12 12M18 6 6 18" /> : null}
      {name === "ring" ? (<><path {...p} d="M5 3h3l2 5-2.5 1.5a11 11 0 0 0 7 7L16 14l5 2v3a2 2 0 0 1-2 2A17 17 0 0 1 3 5a2 2 0 0 1 2-2Z" /><path {...p} d="M15 3.5a5.5 5.5 0 0 1 5.5 5.5M15 7a2 2 0 0 1 2 2" /></>) : null}
      {name === "doc" ? (<><path {...p} d="M6 3h8l4 4v14H6Z" /><path {...p} d="M14 3v4h4M9 12h6M9 16h6" /></>) : null}
      {name === "chat" ? (<><path {...p} d="M4 5h16v11H9l-5 4Z" /><path {...p} d="M8 9.5h8M8 12.5h5" /></>) : null}
      {name === "out" ? (<><path {...p} d="M5 3h3l2 5-2.5 1.5a11 11 0 0 0 7 7L16 14l5 2v3a2 2 0 0 1-2 2A17 17 0 0 1 3 5a2 2 0 0 1 2-2Z" /><path {...p} d="M15 3h6v6M21 3l-7 7" /></>) : null}
      {name === "key" ? (<><rect {...p} x={4} y={4} width={16} height={16} rx={4} /><path {...p} d="M11 9l2-1.5V16" /></>) : null}
    </svg>
  );
};

/** Subtítulos de la locución, abajo al centro (como en docs-intro). */
export const Subtitulos: React.FC = () => {
  const frame = useCurrentFrame();
  let texto = "";
  let o = 0;
  for (const id of Object.keys(SUBS) as VoId[]) {
    const partes = SUBS[id];
    const ini = f(SCENES[ESCENA_DE[id]].from + AT[id]);
    const len = f(DUR[id]);
    if (frame < ini || frame > ini + len + 6) continue;
    const total = partes.reduce((s, p) => s + p.length, 0);
    let acc = ini;
    for (const p of partes) {
      const d = (len * p.length) / total;
      if (frame >= acc && frame < acc + d + (p === partes[partes.length - 1] ? 6 : 0)) {
        texto = p;
        o = interpolate(frame, [ini, ini + 4, ini + len, ini + len + 6], [0, 1, 1, 0], CLAMP);
      }
      acc += d;
    }
  }
  if (!texto) return null;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{ background: "rgba(11,18,32,0.86)", color: "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 30, padding: "9px 22px",
        borderRadius: 12, maxWidth: 1500, textAlign: "center" }}>
        {texto}
      </div>
    </div>
  );
};

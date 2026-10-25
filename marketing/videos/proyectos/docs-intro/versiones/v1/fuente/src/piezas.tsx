import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { AT, DUR, ESCENA_DE, SCENES, SUBS, type VoId } from "./timeline";

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

/** Lo que depende del plan: borde amarillo, como en el panel (DESIGN_GUIDELINE_APP, funciones por plan). */
export const PlanBadge: React.FC<{ children: React.ReactNode; p?: number; style?: React.CSSProperties; dark?: boolean }> = ({ children, p = 1, style, dark }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 12, background: dark ? "#2a2410" : "#fff8e6", border: "2px solid #e8b931",
    borderRadius: 14, padding: "8px 16px", fontFamily: F.body, fontWeight: 600, fontSize: 22, color: dark ? "#ffe08a" : "#7a5200",
    opacity: p, transform: `translateY(${(1 - p) * 10}px)`, whiteSpace: "nowrap", ...style,
  }}>
    <span style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: dark ? "#ffd04d" : "#a06c00" }}>PLAN</span>
    {children}
  </div>
);

/** Rótulo chico en mono (ilustrativo, fuente de un dato). */
export const Nota: React.FC<{ children: React.ReactNode; p?: number; style?: React.CSSProperties; color?: string }> = ({ children, p = 1, style, color = C.muted }) => (
  <div style={{ fontFamily: F.mono, fontSize: 18, color, opacity: p, letterSpacing: "0.02em", ...style }}>{children}</div>
);

export const Scope: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ fontFamily: F.mono, fontSize: 20, background: C.accentSoft, color: C.accent2, borderRadius: 8, padding: "2px 10px" }}>{children}</span>
);

/** Subtítulos de la locución, abajo al centro (como en api-desarrolladores). */
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

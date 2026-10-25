import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CodeLine } from "../../../src/comun/code";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { AT, DUR, ESCENA_DE, SCENES, SUBS, type VoId } from "./timeline";

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

/** Código que aparece línea por línea, con líneas resaltadas por tramos (de api-desarrolladores). */
export const Code: React.FC<{
  text: string; at?: number; stagger?: number; hl?: { a: number; b: number; lines: number[] }[]; base?: string;
}> = ({ text, at = 0.2, stagger = 0.035, hl = [], base }) => {
  const t = useT();
  return (
    <>
      {text.split("\n").map((l, i) => {
        const o = interpolate(t, [at + i * stagger, at + i * stagger + 0.25], [0, 1], CLAMP);
        const h = Math.max(0, ...hl.filter((x) => x.lines.includes(i)).map((x) =>
          interpolate(t, [x.a, x.a + 0.25, x.b - 0.25, x.b], [0, 1, 1, 0], CLAMP)));
        const dim = hl.some((x) => t > x.a && t < x.b) ? 1 - 0.45 * (1 - h) : 1;
        return (
          <div key={i} style={{ opacity: o * dim, transform: `translateX(${(1 - o) * 10}px)`, position: "relative" }}>
            <div style={{ position: "absolute", left: -22, right: -22, top: 0, bottom: 0, background: "rgba(157,182,255,0.16)",
              borderLeft: `4px solid ${C.accentOnDark}`, opacity: h }} />
            <div style={{ position: "relative" }}><CodeLine line={l} base={base} /></div>
          </div>
        );
      })}
    </>
  );
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

/** Rótulo chico en mono (fuente de un dato, "ejemplo de la documentación"). */
export const Nota: React.FC<{ children: React.ReactNode; p?: number; style?: React.CSSProperties; color?: string }> = ({ children, p = 1, style, color = C.muted }) => (
  <div style={{ fontFamily: F.mono, fontSize: 18, color, opacity: p, letterSpacing: "0.02em", ...style }}>{children}</div>
);

/** Código en línea (nombre de herramienta, header, campo). */
export const Mono: React.FC<{ children: React.ReactNode; size?: number; style?: React.CSSProperties }> = ({ children, size = 22, style }) => (
  <span style={{ fontFamily: F.mono, fontSize: size, background: C.accentSoft, color: C.accent2, borderRadius: 8, padding: "2px 10px", ...style }}>{children}</span>
);

/** Ícono propio del endpoint del cliente (código entre llaves angulares). */
export const IconoCodigo: React.FC<{ size?: number; color?: string }> = ({ size = 44, color = C.accent }) => {
  const p = { fill: "none", stroke: color, strokeWidth: 2.2, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size}>
      <path d="M8.5 7 4 12l4.5 5M15.5 7 20 12l-4.5 5M13.5 5l-3 14" {...p} />
    </svg>
  );
};

/** Subtítulos de la locución, abajo al centro (como en api-desarrolladores y docs-intro). */
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

import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CodeLine } from "../../../src/comun/code";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { useIn } from "../../../src/comun/ui";
import { AT, DUR, SCENES, SUBS } from "./timeline";

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

/** Código que aparece línea por línea en poco tiempo (no letra por letra), con líneas resaltadas por tramos. */
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

/** Lo que depende del plan contratado: borde amarillo, como en el panel (DESIGN_GUIDELINE_APP, funciones por plan). */
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

/** Rótulo chico en mono (fuente de un dato, "respuesta real", "anonimizado"). */
export const Nota: React.FC<{ children: React.ReactNode; p?: number; style?: React.CSSProperties; color?: string }> = ({ children, p = 1, style, color = C.muted }) => (
  <div style={{ fontFamily: F.mono, fontSize: 18, color, opacity: p, letterSpacing: "0.02em", ...style }}>{children}</div>
);

/** Terminal oscura con prompt. */
export const Terminal: React.FC<{ title?: string; children: React.ReactNode; style?: React.CSSProperties; fontSize?: number }> = ({
  title = "terminal", children, style, fontSize = 21,
}) => (
  <div style={{ background: "#070b14", borderRadius: 20, overflow: "hidden", boxShadow: "0 24px 60px rgba(11,18,32,.25)", border: "2px solid #1e2940", ...style }}>
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 16px", background: "#111827" }}>
      {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />)}
      <div style={{ fontFamily: F.mono, fontSize: 17, color: C.ctaMuted, marginLeft: 10 }}>{title}</div>
    </div>
    <div style={{ padding: "16px 20px", fontFamily: F.mono, fontSize, lineHeight: 1.5, color: C.ctaInk, whiteSpace: "pre" }}>{children}</div>
  </div>
);

export const Prompt: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div><span style={{ color: "#5ee49a" }}>$ </span>{children}</div>
);

/** Subtítulos de la locución, abajo al centro: tramos repartidos por largo de texto dentro de cada voz. */
export const Subtitulos: React.FC = () => {
  const frame = useCurrentFrame();
  let texto = "";
  let o = 0;
  for (const [id, partes] of Object.entries(SUBS)) {
    const escena = ESCENA_DE[id];
    const ini = f(SCENES[escena].from + AT[id as keyof typeof AT]);
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

const ESCENA_DE: Record<string, keyof typeof SCENES> = {
  a1: "intro", a2: "capacidades", a3: "auth", a4: "auth", a5: "llm", a6: "tts", demo: "tts", a7: "agente", a8: "llamada",
  a9: "resultado", a10: "webhook", a11: "cierre",
};

/** Entrada simple (opacidad y subida) para un bloque. */
export const In: React.FC<{ at: number; children: React.ReactNode; style?: React.CSSProperties; dy?: number }> = ({ at, children, style, dy = 18 }) => {
  const p = useIn(at, 0.5);
  return <div style={{ opacity: p, transform: `translateY(${(1 - p) * dy}px)`, ...style }}>{children}</div>;
};

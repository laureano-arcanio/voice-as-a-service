import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/laestrella-propuesta/vo/envolventes.json";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { Icon, useIn } from "../../../src/comun/ui";

// Piezas del diagrama, con el lenguaje de la landing (copiadas de simtecuida-analisis): aro de puntos, curvas
// punteadas, paquetes que viajan y baldosas de canal.

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

/** Nivel de la voz `id` (0..1) en el segundo `t` de la escena, si arrancó en `at`. */
export const useHabla = (id: keyof typeof envs, at: number, k = 0.6) => {
  const t = useT();
  const env = envs[id];
  const i = Math.round((t - at) * 30);
  return i >= 0 && i < env.length ? env[i] * k : 0;
};

export type Pt = { x: number; y: number };
export type Curva = { a: Pt; c: Pt; b: Pt };
const q = (k: number, { a, c, b }: Curva): Pt => ({
  x: (1 - k) ** 2 * a.x + 2 * (1 - k) * k * c.x + k ** 2 * b.x,
  y: (1 - k) ** 2 * a.y + 2 * (1 - k) * k * c.y + k ** 2 * b.y,
});
export const d = ({ a, c, b }: Curva) => `M ${a.x} ${a.y} Q ${c.x} ${c.y} ${b.x} ${b.y}`;
/** Curva recta entre dos puntos. */
export const recta = (a: Pt, b: Pt): Curva => ({ a, b, c: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 } });

/** Trazo punteado que corre, con opacidad. */
export const Traza: React.FC<{ curva: Curva; o: number; dash?: string }> = ({ curva, o, dash = "3 13" }) => {
  const frame = useCurrentFrame();
  return <path d={d(curva)} stroke={C.accent} strokeWidth={5} strokeDasharray={dash} strokeDashoffset={-frame * 1.2} strokeLinecap="round" fill="none" opacity={o * 0.75} />;
};

export const Paquete: React.FC<{ t: number; curva: Curva; a: number; b: number; color?: string; children: React.ReactNode }> = ({ t, curva, a, b, color = C.accent, children }) => {
  if (t < a - 0.1 || t > b + 0.25) return null;
  const k = interpolate(t, [a, b], [0, 1], { ...CLAMP, easing: EASE });
  const p = q(k, curva);
  const o = Math.min(interpolate(t, [a - 0.1, a + 0.05], [0, 1], CLAMP), interpolate(t, [b, b + 0.25], [1, 0], CLAMP));
  return (
    <div style={{
      position: "absolute", left: p.x, top: p.y, transform: "translate(-50%, -50%)", opacity: o, background: color, color: "#fff", borderRadius: 999,
      padding: "8px 16px", fontFamily: F.mono, fontSize: 22, display: "flex", alignItems: "center", gap: 8, boxShadow: "0 8px 20px rgba(36,86,230,0.35)", whiteSpace: "nowrap",
    }}>
      {children}
    </div>
  );
};

export const Aro: React.FC<{ t: number; cx: number; cy: number; r: number; on: number }> = ({ t, cx, cy, r, on }) => {
  const n = 40;
  const head = (t * 9) % n;
  return (
    <svg width={r * 2 + 30} height={r * 2 + 30} style={{ position: "absolute", left: cx - r - 15, top: cy - r - 15, overflow: "visible", opacity: on }}>
      {Array.from({ length: n }).map((_, i) => {
        const ang = (i / n) * Math.PI * 2 - Math.PI / 2;
        const dd = (head - i + n) % n;
        const lit = Math.max(0, 1 - dd / 9);
        return <circle key={i} cx={r + 15 + r * Math.cos(ang)} cy={r + 15 + r * Math.sin(ang)} r={5 + 2 * lit} fill={lit > 0.05 ? C.accent : C.line2} opacity={0.55 + 0.45 * lit} />;
      })}
    </svg>
  );
};

/** Ícono en su baldosa con degradé, como en la sección Canales de la home. */
export const Baldosa: React.FC<{ children: React.ReactNode; size?: number; gris?: boolean }> = ({ children, size = 64, gris }) => (
  <div style={{
    width: size, height: size, flexShrink: 0, borderRadius: size * 0.28, display: "flex", alignItems: "center", justifyContent: "center",
    background: gris ? "linear-gradient(135deg, #94a3b8, #64748b)" : "linear-gradient(135deg, #5b86ff, #2456e6)", boxShadow: "0 8px 16px rgba(11,18,32,.12)",
  }}>
    {children}
  </div>
);

/** Persona (pasajero), en trazo. */
export const Pasajero: React.FC<{ size?: number; color?: string }> = ({ size = 40, color = "#fff" }) => (
  <svg viewBox="0 0 24 24" width={size} height={size}>
    <circle cx={12} cy={8} r={4} fill={color} />
    <path d="M4 21a8 8 0 0 1 16 0Z" fill={color} />
  </svg>
);

/** Teléfono de escritorio (el teléfono IP de la sucursal). */
export const TelefonoIP: React.FC<{ size?: number; color?: string }> = ({ size = 40, color = "#fff" }) => {
  const p = { fill: "none", stroke: color, strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size}>
      <path {...p} d="M4 9c0-3 3.5-5 8-5s8 2 8 5v1.5h-4V8.5c-1-.6-2.4-1-4-1s-3 .4-4 1v2H4Z" />
      <path {...p} d="M7 11h10l2.5 8.5a1 1 0 0 1-1 1.3h-13a1 1 0 0 1-1-1.3Z" />
      <path {...p} d="M10 14h.01M12 14h.01M14 14h.01M10 16.5h.01M12 16.5h.01M14 16.5h.01" strokeWidth={2.6} />
    </svg>
  );
};

export { Icon };

/** Pie como el del PDF. */
export const Pie: React.FC<{ fuente?: string }> = ({ fuente }) => {
  const o = useIn(0.5, 0.5);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · EMPRESA LA ESTRELLA</span>
    </div>
  );
};

/** Rótulo en mono, chico. */
export const Rotulo: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({ children, color = C.accent, style }) => (
  <div style={{ fontFamily: F.mono, fontSize: 21, letterSpacing: "0.08em", textTransform: "uppercase", color, ...style }}>{children}</div>
);

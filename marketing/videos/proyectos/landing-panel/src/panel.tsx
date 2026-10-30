import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";

/**
 * El panel recreado (web/: AppLayout, nav.ts, Mantine con los tokens de DESIGN_GUIDELINE_APP), en una ventana que
 * la cámara recorre. Las medidas son de la ventana (WIN); la cámara la escala y la mueve dentro del cuadro.
 */

export const WIN = { w: 1100, h: 1400 };
export const HEADER = 78;
export const SIDEBAR = 300;
export const CANVAS = "#f6f8fb";
// Cuadro vertical 4:5 (1080 x 1350): centro de la cámara abajo del título
export const CUADRO = { w: 1080, h: 1350 };
const CAM_X = 540;
const CAM_Y = 675;
// Zoom 1 = la ventana entera en el cuadro, con margen blanco (v5: sin títulos y con poco zoom, pedido del usuario)
export const BASE = 0.94;

export const useT = () => useCurrentFrame() / useVideoConfig().fps;

/** 0 → 1 entre a y a + d (s), con la curva de la marca. */
export const ein = (t: number, a: number, d = 0.4) => interpolate(t, [a, a + d], [0, 1], { ...CLAMP, easing: EASE });

/** Pop con resorte desde el segundo `at` (local). */
export const usePopAt = (at: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - at * fps, fps, config: { damping: 13, stiffness: 170 } });
};

export type Cam = { t: number; s: number; x: number; y: number };

const camAt = (keys: Cam[], t: number) => {
  if (t <= keys[0].t) return keys[0];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1];
    const b = keys[i];
    if (t <= b.t) {
      const k = interpolate(t, [a.t, b.t], [0, 1], { ...CLAMP, easing: EASE });
      return { t, s: a.s + (b.s - a.s) * k, x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k };
    }
  }
  return keys[keys.length - 1];
};

/** La ventana del panel con la cámara: (x, y) de la ventana queda en el centro del cuadro, con zoom s (1 = la ventana entera). */
export const Camara: React.FC<{ keys: Cam[]; children: React.ReactNode }> = ({ keys, children }) => {
  const t = useT();
  const k = camAt(keys, t);
  const c = { ...k, s: k.s * BASE };
  return (
    <div style={{
      position: "absolute", left: CAM_X - c.x * c.s, top: CAM_Y - c.y * c.s, width: WIN.w, height: WIN.h,
      transform: `scale(${c.s})`, transformOrigin: "0 0",
    }}>
      {children}
    </div>
  );
};

type NavId = "inicio" | "reportes" | "conversaciones" | "agentes" | "herramientas" | "voces" | "equipo" | "whatsapp";

const NAV: ({ id: NavId; label: string; sub?: boolean } | { grupo: string })[] = [
  { id: "inicio", label: "Inicio" },
  { id: "reportes", label: "Reportes" },
  { id: "conversaciones", label: "Conversaciones" },
  { grupo: "Agentes" },
  { id: "agentes", label: "Mis agentes", sub: true },
  { id: "herramientas", label: "Herramientas", sub: true },
  { id: "voces", label: "Voces", sub: true },
  { grupo: "Canales" },
  { id: "whatsapp", label: "WhatsApp", sub: true },
  { grupo: "Agenda" },
  { id: "equipo", label: "Equipo", sub: true },
];

/** Marco del panel: header con la marca, menú del cliente (CLIENT_NAV) y el lienzo. */
export const AppFrame: React.FC<{ activo: NavId; children: React.ReactNode }> = ({ activo, children }) => (
  <div style={{
    position: "absolute", inset: 0, background: CANVAS, borderRadius: 26, overflow: "hidden",
    border: `2px solid ${C.line}`, fontFamily: F.body, color: C.ink,
  }}>
    <div style={{
      position: "absolute", left: 0, right: 0, top: 0, height: HEADER, background: "#fff", borderBottom: `2px solid ${C.line}`,
      display: "flex", alignItems: "center", padding: "0 30px", gap: 16,
    }}>
      <Img src={staticFile("marca/atentina-logo.svg")} style={{ height: 38 }} />
      <div style={{ flex: 1 }} />
      <div style={{
        width: 46, height: 46, borderRadius: 23, background: C.accentSoft, color: C.accent, display: "grid",
        placeItems: "center", fontWeight: 800, fontSize: 19,
      }}>AN</div>
    </div>
    <div style={{
      position: "absolute", left: 0, top: HEADER, bottom: 0, width: SIDEBAR, background: "#fff",
      borderRight: `2px solid ${C.line}`, padding: "22px 16px",
    }}>
      {NAV.map((n, i) =>
        "grupo" in n ? (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 14px", fontSize: 24, fontWeight: 600, color: C.ink2 }}>
            <Glifo /> {n.grupo}
          </div>
        ) : (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 14, padding: "12px 14px", marginLeft: n.sub ? 26 : 0, borderRadius: 10,
            fontSize: 24, fontWeight: n.id === activo ? 700 : 500,
            background: n.id === activo ? C.accentSoft : "transparent", color: n.id === activo ? C.accent : C.ink2,
          }}>
            {n.sub ? null : <Glifo activo={n.id === activo} />} {n.label}
          </div>
        ),
      )}
    </div>
    <div style={{ position: "absolute", left: SIDEBAR, top: HEADER, right: 0, bottom: 0, padding: "34px 44px" }}>{children}</div>
  </div>
);

/** Ícono neutro del menú (un cuadrado redondeado de trazo). */
const Glifo: React.FC<{ activo?: boolean }> = ({ activo }) => (
  <svg width={24} height={24} viewBox="0 0 24 24">
    <rect x={4} y={4} width={16} height={16} rx={5} fill="none" stroke={activo ? C.accent : C.muted} strokeWidth={2.2} />
  </svg>
);

export const PageTitle: React.FC<{ children: React.ReactNode; sub?: string; derecha?: React.ReactNode }> = ({ children, sub, derecha }) => (
  <div style={{ display: "flex", alignItems: "flex-end", marginBottom: 24 }}>
    <div style={{ flex: 1 }}>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 46, letterSpacing: "-0.015em", lineHeight: 1.1 }}>{children}</div>
      {sub ? <div style={{ fontSize: 23, color: C.muted, marginTop: 6 }}>{sub}</div> : null}
    </div>
    {derecha}
  </div>
);

export const Tarjeta: React.FC<{ titulo?: string; desc?: string; style?: React.CSSProperties; children: React.ReactNode }> = ({ titulo, desc, style, children }) => (
  <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "24px 28px", ...style }}>
    {titulo ? <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, marginBottom: desc ? 4 : 16 }}>{titulo}</div> : null}
    {desc ? <div style={{ fontSize: 20, color: C.muted, marginBottom: 18 }}>{desc}</div> : null}
    {children}
  </div>
);

/** Campo de texto de Mantine: etiqueta arriba y el valor; con `escribe`, el texto aparece letra por letra. */
export const Campo: React.FC<{
  label: string; valor: string; t?: number; escribe?: [number, number]; foco?: boolean; mono?: boolean;
  style?: React.CSSProperties; alto?: number;
}> = ({ label, valor, t = 99, escribe, foco, mono, style, alto = 60 }) => {
  const frame = useCurrentFrame();
  const n = escribe ? Math.round(interpolate(t, escribe, [0, valor.length], CLAMP)) : valor.length;
  const escribiendo = escribe ? t >= escribe[0] && t <= escribe[1] + 0.4 : false;
  return (
    <div style={style}>
      <div style={{ fontSize: 22, fontWeight: 600, color: C.ink, marginBottom: 8 }}>{label}</div>
      <div style={{
        minHeight: alto, borderRadius: 10, border: `2px solid ${foco || escribiendo ? C.accent : C.line2}`, background: "#fff",
        padding: "10px 16px", display: "flex", alignItems: "center", boxSizing: "border-box",
        fontFamily: mono ? F.mono : F.body, fontSize: mono ? 23 : 25, color: C.ink, whiteSpace: "nowrap", overflow: "hidden",
      }}>
        {valor.slice(0, n)}
        {escribiendo && frame % 20 < 12 ? <span style={{ display: "inline-block", width: 2.5, height: 28, background: C.accent, marginLeft: 2 }} /> : null}
      </div>
    </div>
  );
};

export const Boton: React.FC<{ children: React.ReactNode; tipo?: "primario" | "default" | "rojo"; style?: React.CSSProperties; presion?: number }> = ({
  children, tipo = "primario", style, presion = 0,
}) => (
  <div style={{
    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 10, height: 58, padding: "0 26px",
    borderRadius: 10, fontWeight: 700, fontSize: 24, whiteSpace: "nowrap",
    background: tipo === "primario" ? C.accent : tipo === "rojo" ? C.warn : "#fff",
    color: tipo === "default" ? C.ink : "#fff", border: tipo === "default" ? `2px solid ${C.line2}` : "none",
    transform: `scale(${1 - presion * 0.06})`, ...style,
  }}>{children}</div>
);

export const Badge: React.FC<{ color?: "gray" | "green" | "blue" | "yellow"; children: React.ReactNode; style?: React.CSSProperties }> = ({ color = "gray", children, style }) => {
  const c = {
    gray: { bg: "#eef1f5", fg: C.ink2 },
    green: { bg: "#e3f4ea", fg: "#147a46" },
    blue: { bg: C.accentSoft, fg: C.accent },
    yellow: { bg: "#fdf0e3", fg: "#ad5008" },
  }[color];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 8, background: c.bg, color: c.fg, borderRadius: 8, padding: "4px 12px",
      fontSize: 18, fontWeight: 700, letterSpacing: "0.03em", textTransform: "uppercase", whiteSpace: "nowrap", ...style,
    }}>{children}</span>
  );
};

/** Pestañas de Mantine (las del agente o las de Reportes). */
export const Pestanas: React.FC<{ items: string[]; activa: string; style?: React.CSSProperties }> = ({ items, activa, style }) => (
  <div style={{ display: "flex", gap: 6, borderBottom: `2px solid ${C.line}`, marginBottom: 26, overflow: "hidden", ...style }}>
    {items.map((i) => (
      <div key={i} style={{
        padding: "12px 12px", fontSize: 21, fontWeight: i === activa ? 700 : 500, whiteSpace: "nowrap",
        color: i === activa ? C.accent : C.ink2, borderBottom: `3px solid ${i === activa ? C.accent : "transparent"}`, marginBottom: -2,
      }}>{i}</div>
    ))}
  </div>
);

export type RetratoId = "sofia" | "paula" | "carolina" | "martin" | "diego" | "mateo" | "valentina" | "lucas";

/** Retrato de una voz (web/public/voces/, el mismo que usa el panel). */
export const Retrato: React.FC<{ id: RetratoId; size: number; anillo?: string; style?: React.CSSProperties }> = ({ id, size, anillo, style }) => (
  <div style={{
    width: size, height: size, borderRadius: "50%", flexShrink: 0, background: "#fff",
    boxShadow: anillo ? `0 0 0 ${Math.max(3, size / 26)}px ${anillo}` : undefined, ...style,
  }}>
    <Img src={staticFile(`proyectos/landing-panel/voces/${id}.svg`)} style={{ width: size, height: size, borderRadius: "50%" }} />
  </div>
);

/** El cursor: se mueve por los puntos (coordenadas de la ventana) y hace click con un aro. */
export const Cursor: React.FC<{ ruta: { t: number; x: number; y: number }[]; clicks?: number[]; de?: number; hasta?: number }> = ({
  ruta, clicks = [], de = 0, hasta = 99,
}) => {
  const t = useT();
  let p = ruta[0];
  for (let i = 1; i < ruta.length; i++) {
    const a = ruta[i - 1];
    const b = ruta[i];
    if (t >= a.t && t <= b.t) {
      const k = interpolate(t, [a.t, b.t], [0, 1], { ...CLAMP, easing: EASE });
      p = { t, x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k };
    } else if (t > b.t) p = b;
  }
  const o = Math.min(interpolate(t, [de, de + 0.2], [0, 1], CLAMP), interpolate(t, [hasta, hasta + 0.25], [1, 0], CLAMP));
  const click = clicks.find((c) => t >= c && t < c + 0.5);
  const k = click === undefined ? 1 : interpolate(t, [click, click + 0.5], [0, 1], CLAMP);
  const presion = click === undefined ? 0 : interpolate(t, [click, click + 0.08, click + 0.2], [0, 1, 0], CLAMP);
  return (
    <div style={{ position: "absolute", left: p.x, top: p.y, opacity: o, zIndex: 20, pointerEvents: "none" }}>
      {click !== undefined ? (
        <div style={{
          position: "absolute", left: -34, top: -34, width: 68, height: 68, borderRadius: 34, border: `5px solid ${C.accent}`,
          opacity: 1 - k, transform: `scale(${0.3 + k * 1.1})`,
        }} />
      ) : null}
      <svg width={44} height={54} viewBox="0 0 24 30" style={{ transform: `scale(${1 - presion * 0.15})`, transformOrigin: "4px 2px", filter: "drop-shadow(0 4px 6px rgba(11,18,32,.35))" }}>
        <path d="M4 2 L4 24 L10 18 L14 27 L18 25 L14 16 L22 16 Z" fill="#ffffff" stroke={C.ink} strokeWidth={1.7} strokeLinejoin="round" />
      </svg>
    </div>
  );
};

/** Presión de un click en el segundo `c` (0 → 1 → 0), para el botón que se aprieta. */
export const presionDe = (t: number, c: number) => interpolate(t, [c, c + 0.08, c + 0.22], [0, 1, 0], CLAMP);

/** Bordes del cuadro que se funden a blanco: el video va sin borde sobre la página blanca (cuando el zoom saca la ventana del cuadro). */
export const BordeBlanco: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, zIndex: 29, pointerEvents: "none" }}>
    <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 22, background: "linear-gradient(90deg, #fff, rgba(255,255,255,0))" }} />
    <div style={{ position: "absolute", right: 0, top: 0, bottom: 0, width: 22, background: "linear-gradient(270deg, #fff, rgba(255,255,255,0))" }} />
    <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 22, background: "linear-gradient(180deg, #fff, rgba(255,255,255,0))" }} />
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 22, background: "linear-gradient(0deg, #fff, rgba(255,255,255,0))" }} />
  </div>
);

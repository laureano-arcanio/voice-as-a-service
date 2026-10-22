import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "./theme";

export const useIn = (at: number, dur = 0.6) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return interpolate(frame, [at * fps, (at + dur) * fps], [0, 1], { ...CLAMP, easing: EASE });
};

export const usePop = (at: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - at * fps, fps, config: { damping: 14, stiffness: 160 } });
};

export const Eyebrow: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = C.accent }) => (
  <div style={{ fontFamily: F.mono, fontSize: 24, letterSpacing: "0.08em", textTransform: "uppercase", color }}>
    {children}
  </div>
);

/** Título de escena: rótulo + frase, con la parte destacada en el acento. */
export const Headline: React.FC<{ eyebrow: string; text: string; accent?: string; at?: number; size?: number; out?: number }> = ({
  eyebrow, text, accent, at = 0.1, size = 66, out,
}) => {
  const p = useIn(at, 0.7) * (1 - useIn(out ?? 999, 0.3));
  return (
    <div style={{ position: "absolute", left: 120, top: 76, right: 120, opacity: p, transform: `translateY(${(1 - p) * 24}px)` }}>
      <Eyebrow>{eyebrow}</Eyebrow>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: size, lineHeight: 1.08, color: C.ink, marginTop: 14, letterSpacing: "-0.015em" }}>
        {text} {accent ? <span style={{ color: C.accent }}>{accent}</span> : null}
      </div>
    </div>
  );
};

export const Card: React.FC<{ style?: React.CSSProperties; children: React.ReactNode }> = ({ style, children }) => (
  <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 28, boxShadow: shadowCard, ...style }}>
    {children}
  </div>
);

export const Pill: React.FC<{ bg: string; fg: string; children: React.ReactNode; style?: React.CSSProperties }> = ({
  bg, fg, children, style,
}) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 12, background: bg, color: fg, borderRadius: 999,
    padding: "12px 24px", fontFamily: F.body, fontWeight: 700, fontSize: 28, whiteSpace: "nowrap", ...style,
  }}>
    {children}
  </div>
);

type IconName = "phone" | "wa" | "web" | "ear" | "speaker" | "missed" | "check" | "calendar" | "store" | "clock" | "users" | "upload" | "chart";
export const Icon: React.FC<{ name: IconName; size?: number; color?: string }> = ({ name, size = 32, color = "currentColor" }) => {
  const p = { fill: "none", stroke: color, strokeWidth: 2.2, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size}>
      {name === "phone" || name === "missed" ? (
        <path {...p} d="M5 3h3l2 5-2.5 1.5a11 11 0 0 0 7 7L16 14l5 2v3a2 2 0 0 1-2 2A17 17 0 0 1 3 5a2 2 0 0 1 2-2Z" />
      ) : null}
      {name === "missed" ? <path {...p} d="M15 3l6 6M21 3l-6 6" /> : null}
      {name === "wa" ? (
        <>
          <path {...p} d="M3.5 20.5l1.3-4A8.5 8.5 0 1 1 8 19.6Z" />
          <path {...p} d="M9 8.5c0 3.5 3 6.5 6.5 6.5l1-1.6-2-1-1 .9a4 4 0 0 1-2.8-2.8l.9-1-1-2Z" strokeWidth={1.6} />
        </>
      ) : null}
      {name === "web" ? (
        <>
          <rect {...p} x={3} y={4} width={18} height={16} rx={3} />
          <path {...p} d="M3 9h18M6.5 6.5h.01M9 6.5h.01" />
        </>
      ) : null}
      {name === "ear" ? (
        <>
          <path {...p} d="M7 9a5 5 0 0 1 10 0c0 3-3 4-3 7a3 3 0 0 1-5 2" />
          <path {...p} d="M10 9.5a2 2 0 0 1 4 0c0 1.5-1.5 2-1.5 3" />
        </>
      ) : null}
      {name === "speaker" ? (
        <>
          <path {...p} d="M4 9h4l5-4v14l-5-4H4Z" />
          <path {...p} d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" />
        </>
      ) : null}
      {name === "check" ? <path {...p} d="M5 12.5l4.5 4.5L19 7.5" /> : null}
      {name === "calendar" ? (
        <>
          <rect {...p} x={3.5} y={5} width={17} height={15} rx={3} />
          <path {...p} d="M3.5 10h17M8 3v4M16 3v4M8 14h2M12 14h2M16 14h.01" />
        </>
      ) : null}
      {name === "store" ? (
        <>
          <path {...p} d="M4 9l1.5-5h13L20 9M4 9h16v2a3 3 0 0 1-5.3 1.9A3 3 0 0 1 12 14a3 3 0 0 1-2.7-1.1A3 3 0 0 1 4 11Z" />
          <path {...p} d="M5.5 14v6h13v-6M10 20v-4h4v4" />
        </>
      ) : null}
      {name === "users" ? (
        <>
          <circle {...p} cx={9} cy={8} r={3.5} />
          <path {...p} d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5" />
        </>
      ) : null}
      {name === "upload" ? (
        <>
          <path {...p} d="M12 15V4M7.5 8.5 12 4l4.5 4.5" />
          <path {...p} d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
        </>
      ) : null}
      {name === "chart" ? (
        <>
          <path {...p} d="M4 4v16h16" />
          <path {...p} d="M8 16v-4M12 16V8M16 16v-6" />
        </>
      ) : null}
      {name === "clock" ? (
        <>
          <circle {...p} cx={12} cy={13} r={8} />
          <path {...p} d="M12 9v4l2.5 2M10 2.5h4" />
        </>
      ) : null}
    </svg>
  );
};

/** Onda de audio animada (barras), para "la voz" viajando. */
export const Wave: React.FC<{ n?: number; h?: number; color?: string; live?: number }> = ({ n = 7, h = 34, color = "#fff", live = 1 }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5, height: h }}>
      {Array.from({ length: n }).map((_, i) => {
        const k = 0.25 + 0.75 * live * Math.abs(Math.sin(frame / 3 + i * 1.3));
        return <div key={i} style={{ width: 7, height: h * k, borderRadius: 4, background: color }} />;
      })}
    </div>
  );
};

/** Globo de diálogo con piquito hacia abajo a la izquierda. */
export const Bubble: React.FC<{ children: React.ReactNode; style?: React.CSSProperties; bg?: string; fg?: string }> = ({
  children, style, bg = "#fff", fg = C.ink,
}) => (
  <div style={{ position: "absolute", ...style }}>
    <div style={{
      background: bg, color: fg, border: `2px solid ${C.line}`, borderRadius: 26, padding: "16px 26px",
      fontFamily: F.body, fontWeight: 600, fontSize: 30, boxShadow: shadowCard, whiteSpace: "nowrap",
    }}>
      {children}
    </div>
    <svg width={34} height={22} style={{ position: "absolute", left: 34, bottom: -20 }}>
      <path d="M0 0 L34 0 L4 22 Z" fill={bg} />
      <path d="M0 1 L4 22 L34 1" fill="none" stroke={C.line} strokeWidth={2} />
    </svg>
  </div>
);

export const Backdrop: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, background: `linear-gradient(180deg, ${C.bg2} 0%, ${C.bg} 70%)` }}>
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.55 }}>
      <defs>
        <pattern id="dots" width={36} height={36} patternUnits="userSpaceOnUse">
          <circle cx={2} cy={2} r={1.6} fill={C.line2} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#dots)" />
    </svg>
  </div>
);

/** Curva punteada que "corre" (el trazo avanza con el frame). */
export const Link: React.FC<{ d: string; color: string; opacity: number; width?: number }> = ({ d, color, opacity, width = 5 }) => {
  const frame = useCurrentFrame();
  return (
    <path d={d} stroke={color} strokeWidth={width} strokeDasharray="3 13" strokeDashoffset={-frame * 1.5} strokeLinecap="round"
      fill="none" opacity={opacity} />
  );
};

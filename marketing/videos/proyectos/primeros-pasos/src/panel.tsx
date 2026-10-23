import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { useIn } from "../../../src/comun/ui";

// Medidas del teléfono dentro del cuadro vertical (1080 x 1920). La pantalla útil mide 716 x 1386.
export const PHONE = { left: 170, top: 380, w: 740, h: 1410 };
export const SCREEN = { w: 716, h: 1386 };

export const useT = () => useCurrentFrame() / useVideoConfig().fps;

export const Phone: React.FC<{ children: React.ReactNode; scale?: number; origin?: string }> = ({
  children, scale = 1, origin = "50% 40%",
}) => (
  <div
    style={{
      position: "absolute", left: PHONE.left, top: PHONE.top, width: PHONE.w, height: PHONE.h,
      background: C.ink, borderRadius: 64, padding: 12, boxShadow: "0 34px 90px rgba(11,18,32,.30)",
      transform: `scale(${scale})`, transformOrigin: origin,
    }}
  >
    <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 52, overflow: "hidden", background: C.bg2 }}>
      {children}
    </div>
  </div>
);

export const AppBar: React.FC = () => (
  <div style={{ height: 64, display: "flex", alignItems: "center", gap: 10, padding: "0 22px", background: "#fff", borderBottom: `1px solid ${C.line}` }}>
    <AgenteLogo size={34} />
    <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 24, letterSpacing: "-0.02em", color: C.ink }}>Atentina</div>
    <div style={{ flex: 1 }} />
    <div style={{
      width: 34, height: 34, borderRadius: 17, background: C.accentSoft, color: C.accent,
      display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, fontWeight: 800,
    }}>AC</div>
  </div>
);

export const Body: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ padding: "20px 22px", ...style }}>{children}</div>
);

/** Título de la escena, fuera del teléfono. */
export const Titulo: React.FC<{ eyebrow: string; text: string; accent?: string; at?: number; size?: number }> = ({
  eyebrow, text, accent, at = 0.1, size = 57,
}) => {
  const p = useIn(at, 0.7);
  return (
    <div style={{ position: "absolute", left: 84, top: 82, right: 84, opacity: p, transform: `translateY(${(1 - p) * 22}px)` }}>
      <div style={{ fontFamily: F.mono, fontSize: 22, letterSpacing: "0.09em", textTransform: "uppercase", color: C.accent }}>{eyebrow}</div>
      <div style={{
        fontFamily: F.display, fontWeight: 800, fontSize: size, lineHeight: 1.06, color: C.ink,
        marginTop: 12, letterSpacing: "-0.015em",
      }}>
        {text} {accent ? <span style={{ color: C.accent }}>{accent}</span> : null}
      </div>
    </div>
  );
};

export const Btn: React.FC<{
  children: React.ReactNode; primary?: boolean; disabled?: boolean; style?: React.CSSProperties; h?: number;
}> = ({ children, primary, disabled, style, h = 58 }) => (
  <div style={{
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8, height: h, padding: "0 20px",
    borderRadius: 12, fontFamily: F.body, fontWeight: 700, fontSize: 25,
    background: primary ? (disabled ? C.line2 : C.accent) : "#fff",
    color: primary ? "#fff" : C.ink2,
    border: primary ? "none" : `2px solid ${C.line2}`,
    boxShadow: primary && !disabled ? "0 8px 18px rgba(36,86,230,.24)" : undefined,
    ...style,
  }}>{children}</div>
);

export const Input: React.FC<{
  label?: string; value?: string; placeholder?: string; focused?: boolean; disabled?: boolean; caret?: boolean;
  style?: React.CSSProperties;
}> = ({ label, value, placeholder, focused, disabled, caret, style }) => {
  const frame = useCurrentFrame();
  const show = caret && frame % 30 < 16;
  return (
    <div style={style}>
      {label ? <div style={{ fontSize: 19, fontWeight: 700, color: C.ink2, marginBottom: 6 }}>{label}</div> : null}
      <div style={{
        height: 56, borderRadius: 11, border: `2px solid ${focused ? C.accent : C.line2}`,
        background: disabled ? C.surface2 : "#fff", padding: "0 13px", display: "flex", alignItems: "center",
        fontFamily: F.body, fontSize: 25, color: value ? C.ink : C.muted,
        boxShadow: focused ? `0 0 0 4px ${C.accentSoft}` : undefined,
      }}>
        <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {value || placeholder}
          {show ? <span style={{ display: "inline-block", width: 2, height: 27, background: C.accent, marginLeft: 2, verticalAlign: "middle" }} /> : null}
        </span>
      </div>
    </div>
  );
};

export const RadioCard: React.FC<{
  title: string; desc: string; selected?: boolean; style?: React.CSSProperties;
}> = ({ title, desc, selected, style }) => (
  <div style={{
    border: `2px solid ${selected ? C.accent : C.line}`, background: selected ? C.accentSoft : "#fff",
    borderRadius: 13, padding: "10px 12px", display: "flex", gap: 10, alignItems: "flex-start", ...style,
  }}>
    <div style={{
      width: 20, height: 20, borderRadius: 10, border: `2px solid ${selected ? C.accent : C.line2}`,
      background: "#fff", marginTop: 3, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
    }}>
      {selected ? <div style={{ width: 10, height: 10, borderRadius: 5, background: C.accent }} /> : null}
    </div>
    <div>
      <div style={{ fontSize: 24, fontWeight: 700, color: C.ink, lineHeight: 1.1 }}>{title}</div>
      <div style={{ fontSize: 18, color: C.muted, lineHeight: 1.2, marginTop: 3 }}>{desc}</div>
    </div>
  </div>
);

export const SwitchUI: React.FC<{ on: boolean }> = ({ on }) => (
  <div style={{
    width: 58, height: 34, borderRadius: 17, background: on ? C.accent : C.line2, padding: 3, flexShrink: 0,
    transition: "none",
  }}>
    <div style={{ width: 28, height: 28, borderRadius: 14, background: "#fff", transform: `translateX(${on ? 24 : 0}px)`, boxShadow: "0 2px 4px rgba(0,0,0,.2)" }} />
  </div>
);

export const CardUI: React.FC<{
  children: React.ReactNode; style?: React.CSSProperties; pad?: number;
}> = ({ children, style, pad = 16 }) => (
  <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: pad, boxShadow: shadowCard, ...style }}>
    {children}
  </div>
);

export const Chip: React.FC<{ children: React.ReactNode; active?: boolean; style?: React.CSSProperties }> = ({
  children, active, style,
}) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 12px", borderRadius: 10,
    border: `2px solid ${active ? C.accent : C.line}`, background: active ? C.accentSoft : "#fff",
    color: active ? C.accent : C.ink2, fontFamily: F.body, fontWeight: 700, fontSize: 19, ...style,
  }}>{children}</div>
);

export const Toast: React.FC<{ at: number; title: string; sub: string }> = ({ at, title, sub }) => {
  const p = useIn(at, 0.35);
  return (
    <div style={{
      position: "absolute", left: 20, right: 20, top: 78, zIndex: 6, opacity: p,
      transform: `translateY(${(1 - p) * -14}px)`, background: C.okSoft, border: `1.5px solid ${C.ok}`,
      borderRadius: 14, padding: "12px 14px", display: "flex", gap: 10, alignItems: "flex-start",
      boxShadow: "0 14px 30px rgba(11,18,32,.16)",
    }}>
      <div style={{
        width: 30, height: 30, borderRadius: 15, background: C.ok, color: "#fff", display: "flex",
        alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 18, flexShrink: 0,
      }}>✓</div>
      <div>
        <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 22, color: C.ink }}>{title}</div>
        <div style={{ fontFamily: F.body, fontSize: 18, color: C.ink2, marginTop: 1 }}>{sub}</div>
      </div>
    </div>
  );
};

export const Cursor: React.FC<{ x: number; y: number; at: number; click?: number }> = ({ x, y, at, click }) => {
  const t = useT();
  const op = interpolate(t, [at, at + 0.25], [0, 1], CLAMP);
  const c = click === undefined ? 0 : interpolate(t, [click, click + 0.45], [0, 1], CLAMP);
  const gone = click === undefined ? 1 : interpolate(t, [click + 0.6, click + 0.9], [1, 0], CLAMP);
  return (
    <div style={{ position: "absolute", left: x, top: y, opacity: op * gone, zIndex: 8 }}>
      {click !== undefined && t >= click && c < 1 ? (
        <div style={{
          position: "absolute", left: -22, top: -22, width: 68, height: 68, borderRadius: 34,
          border: `4px solid ${C.accent}`, opacity: 1 - c, transform: `scale(${0.35 + c * 0.9})`,
        }} />
      ) : null}
      <svg width={38} height={46} viewBox="0 0 24 30" style={{ filter: "drop-shadow(0 3px 4px rgba(11,18,32,.35))" }}>
        <path d="M4 2 L4 24 L10 18 L14 27 L18 25 L14 16 L22 16 Z" fill="#ffffff" stroke={C.ink} strokeWidth={1.7} strokeLinejoin="round" />
      </svg>
    </div>
  );
};

export const TabsBar: React.FC<{ active: string }> = ({ active }) => {
  const items = ["Resumen", "Definición", "Versiones", "Probar", "Link"];
  return (
    <div style={{ display: "flex", gap: 2, padding: "0 12px", background: "#fff", borderBottom: `1px solid ${C.line}` }}>
      {items.map((i) => (
        <div key={i} style={{
          padding: "11px 8px", fontFamily: F.body, fontWeight: 700, fontSize: 18,
          color: i === active ? C.accent : C.muted, borderBottom: `3px solid ${i === active ? C.accent : "transparent"}`,
          whiteSpace: "nowrap",
        }}>{i}</div>
      ))}
    </div>
  );
};

export const Section: React.FC<{ title: string; children: React.ReactNode; style?: React.CSSProperties }> = ({ title, children, style }) => (
  <CardUI style={style} pad={14}>
    <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 24, color: C.ink, marginBottom: 9 }}>{title}</div>
    {children}
  </CardUI>
);

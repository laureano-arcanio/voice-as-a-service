import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { useIn } from "../../../src/comun/ui";

// Capturas reales del panel en un teléfono de 390 x 844 (CSS px, sacadas con DPR 2: 780 x 1688).
// En el cuadro vertical (1080 x 1920) la pantalla mide 640 x 1385: 1 px CSS = 640/390 px.
export const VIEW = { w: 390, h: 844 };
const SCREEN_W = 640;
const K = SCREEN_W / VIEW.w;
const SCREEN_H = Math.round(VIEW.h * K);
const BEZEL = 12;
export const PHONE = { left: (1080 - SCREEN_W - 2 * BEZEL) / 2, top: 410, w: SCREEN_W + 2 * BEZEL, h: SCREEN_H + 2 * BEZEL };

export const useT = () => useCurrentFrame() / useVideoConfig().fps;

/** Una captura que entra en `from` (s) con un fundido corto. La primera de la lista no se funde. */
export type Paso = { img: string; from: number };
/** Toque: un círculo que se achica y una onda, en coordenadas CSS de la captura. */
export type Toque = { x: number; y: number; at: number };

const Tap: React.FC<Toque> = ({ x, y, at }) => {
  const t = useT();
  const p = interpolate(t, [at - 0.35, at], [0, 1], CLAMP);
  const ring = interpolate(t, [at, at + 0.5], [0, 1], CLAMP);
  const gone = interpolate(t, [at + 0.35, at + 0.6], [1, 0], CLAMP);
  if (t < at - 0.35 || t > at + 0.6) return null;
  const cx = x * K;
  const cy = y * K;
  return (
    <>
      <div style={{
        position: "absolute", left: cx - 30, top: cy - 30, width: 60, height: 60, borderRadius: 30,
        background: "rgba(36,86,230,.28)", border: `3px solid ${C.accent}`, opacity: p * gone,
        transform: `scale(${1.25 - 0.25 * p})`,
      }} />
      <div style={{
        position: "absolute", left: cx - 30, top: cy - 30, width: 60, height: 60, borderRadius: 30,
        border: `3px solid ${C.accent}`, opacity: (1 - ring) * (ring > 0 ? 1 : 0), transform: `scale(${1 + ring * 1.4})`,
      }} />
    </>
  );
};

/**
 * El teléfono con las capturas de una escena. `zoom`: acercamiento de cámara (escala y punto en CSS px)
 * entre dos momentos; se usa poco.
 */
export const Pantalla: React.FC<{
  pasos: Paso[];
  toques?: Toque[];
  zoom?: { from: number; to: number; scale: number; x: number; y: number };
}> = ({ pasos, toques = [], zoom }) => {
  const t = useT();
  const enter = useIn(0.05, 0.6);
  const z = zoom ? interpolate(t, [zoom.from, zoom.to], [1, zoom.scale], { ...CLAMP, easing: EASE }) : 1;
  const origin = zoom ? `${(BEZEL + zoom.x * K) / PHONE.w * 100}% ${(BEZEL + zoom.y * K) / PHONE.h * 100}%` : "50% 50%";
  return (
    <div style={{
      position: "absolute", left: PHONE.left, top: PHONE.top, width: PHONE.w, height: PHONE.h,
      background: C.ink, borderRadius: 58, padding: BEZEL, boxShadow: "0 34px 90px rgba(11,18,32,.30)",
      opacity: enter, transform: `translateY(${(1 - enter) * 40}px) scale(${z})`, transformOrigin: origin,
    }}>
      <div style={{ position: "relative", width: SCREEN_W, height: SCREEN_H, borderRadius: 46, overflow: "hidden", background: C.bg2 }}>
        {pasos.map((p, i) => {
          const o = i === 0 ? 1 : interpolate(t, [p.from, p.from + 0.25], [0, 1], CLAMP);
          return (
            <Img key={p.img} src={staticFile(`proyectos/derivaciones/capturas/${p.img}.png`)}
              style={{ position: "absolute", inset: 0, width: SCREEN_W, height: SCREEN_H, opacity: o }} />
          );
        })}
        {toques.map((q, i) => <Tap key={i} {...q} />)}
      </div>
    </div>
  );
};

/** Título de la escena (rótulo en mono + frase con el remate en el acento), arriba del teléfono. */
export const Titulo: React.FC<{ eyebrow: string; text: string; accent?: string; at?: number; size?: number }> = ({
  eyebrow, text, accent, at = 0.1, size = 60,
}) => {
  const p = useIn(at, 0.7);
  return (
    <div style={{ position: "absolute", left: 84, top: 86, right: 84, opacity: p, transform: `translateY(${(1 - p) * 22}px)` }}>
      <div style={{ fontFamily: F.mono, fontSize: 24, letterSpacing: "0.09em", textTransform: "uppercase", color: C.accent }}>{eyebrow}</div>
      <div style={{
        fontFamily: F.display, fontWeight: 800, fontSize: size, lineHeight: 1.06, color: C.ink, marginTop: 14,
        letterSpacing: "-0.015em",
      }}>
        {text} {accent ? <span style={{ color: C.accent }}>{accent}</span> : null}
      </div>
    </div>
  );
};

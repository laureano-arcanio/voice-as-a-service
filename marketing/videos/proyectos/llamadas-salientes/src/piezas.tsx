import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { useIn } from "../../../src/comun/ui";
import { AT, DUR, ESCENA_DE, SCENES, SUBS } from "./timeline";

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

const CAP = "proyectos/llamadas-salientes/capturas";

/** Un recuadro sobre la captura, en píxeles de la imagen original (1920 × 1080 o 780 × 1688 en las del celular). */
export type Ring = { x: number; y: number; w: number; h: number; a: number; b: number };

/** Ventana de tiempo con fundido corto de entrada y salida. */
const win = (t: number, a: number, b: number, d = 0.35) => interpolate(t, [a, a + d, b - d, b], [0, 1, 1, 0], CLAMP);

/**
 * Captura real del panel (backend aislado, datos ficticios) dentro de un marco, con un acercamiento suave y
 * recuadros que marcan dónde mirar. Los recuadros viajan con la imagen (mismo transform).
 */
export const Shot: React.FC<{
  src: string; a: number; b: number; left: number; top: number; w: number; h: number; iw?: number; ih?: number;
  zoom?: [number, number]; origin?: string; rings?: Ring[]; radius?: number; border?: boolean; fadeIn?: number;
  /** Tamaño con que se dibuja la imagen entera (por defecto, el del marco) y, con `center`, el origen del zoom queda en el centro del marco. */
  fitW?: number; fitH?: number; center?: boolean;
  /** Cámara por tramos [t, zoom, x, y] (x e y, de 0 a 1, el punto de la imagen que queda al centro del marco): reemplaza a zoom y origin. */
  cam?: [number, number, number, number][];
}> = ({ src, a, b, left, top, w, h, iw = 1920, ih = 1080, zoom = [1, 1.08], origin = "50% 50%", rings = [], radius = 20, border = true, fadeIn = 0.4,
  fitW = w, fitH = h, center = false, cam }) => {
  const t = useT();
  const o = interpolate(t, [a, a + fadeIn, b - 0.4, b], [0, 1, 1, 0], CLAMP);
  const z = interpolate(t, [a, b], zoom, { ...CLAMP, easing: EASE });
  if (o <= 0) return null;
  const [ox, oy] = origin.split(" ").map((v) => parseFloat(v));
  let tr = `${center ? `translate(${w / 2 - (ox / 100) * fitW}px, ${h / 2 - (oy / 100) * fitH}px) ` : ""}scale(${z})`;
  let zz = z;
  if (cam) {
    const ts = cam.map((k) => k[0]);
    const opt = { ...CLAMP, easing: EASE };
    zz = interpolate(t, ts, cam.map((k) => k[1]), opt);
    // el centro se mantiene dentro de la imagen: nunca se ven bordes vacíos
    const fx = Math.min(1 - 0.5 / zz, Math.max(0.5 / zz, interpolate(t, ts, cam.map((k) => k[2]), opt)));
    const fy = Math.min(1 - 0.5 / zz, Math.max(0.5 / zz, interpolate(t, ts, cam.map((k) => k[3]), opt)));
    tr = `translate(${w / 2 - fx * zz * fitW}px, ${h / 2 - fy * zz * fitH}px) scale(${zz})`;
  }
  return (
    <div style={{ position: "absolute", left, top, width: w, height: h, borderRadius: radius, overflow: "hidden", boxShadow: shadowCard,
      border: border ? `2px solid ${C.line}` : "none", opacity: o, background: "#fff" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: fitW, height: fitH, transformOrigin: cam ? "0 0" : origin,
        transform: tr }}>
        <Img src={staticFile(`${CAP}/${src}`)} style={{ position: "absolute", left: 0, top: 0, width: fitW, height: fitH }} />
        {rings.map((r, i) => {
          const p = win(t, r.a, r.b, 0.3);
          if (p <= 0) return null;
          const pulse = 1 + 0.03 * Math.sin(t * 7);
          return (
            <div key={i} style={{
              position: "absolute", left: `${((r.x - 6) / iw) * 100}%`, top: `${((r.y - 6) / ih) * 100}%`,
              width: `${((r.w + 12) / iw) * 100}%`, height: `${((r.h + 12) / ih) * 100}%`, border: `${4 / zz}px solid ${C.accent}`,
              borderRadius: 14 / zz, boxShadow: `0 0 0 ${9 / zz}px rgba(36,86,230,0.16)`, opacity: p, transform: `scale(${pulse})`,
            }} />
          );
        })}
      </div>
    </div>
  );
};

/** Camino en el panel (Agenda › Equipo ›…): se enciende mientras toca. */
export const Ruta: React.FC<{ n: number; titulo: string; ruta: string; a: number; b: number; left: number; top: number; w?: number }> = ({
  n, titulo, ruta, a, b, left, top, w = 440,
}) => {
  const t = useT();
  const p = useIn(a - 0.1, 0.5);
  const on = t >= a && t < b;
  return (
    <div style={{
      position: "absolute", left, top, width: w, background: on ? C.accentSoft : "#fff", border: `2px solid ${on ? C.accent : C.line}`,
      borderRadius: 22, padding: "16px 22px", boxShadow: shadowCard, opacity: p, transform: `translateX(${(1 - p) * 24}px)`,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <span style={{ width: 38, height: 38, borderRadius: 19, background: on ? C.accent : C.line2, color: "#fff", display: "grid", placeItems: "center",
          fontFamily: F.display, fontWeight: 800, fontSize: 22, flexShrink: 0 }}>{n}</span>
        <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 28, color: C.ink, lineHeight: 1.15 }}>{titulo}</span>
      </div>
      <div style={{ fontFamily: F.mono, fontSize: 19, color: on ? C.accent2 : C.muted, marginTop: 10, lineHeight: 1.3 }}>{ruta}</div>
    </div>
  );
};

/** Texto corto con entrada, para destacar un dato al costado. */
export const Dato: React.FC<{ at: number; out?: number; left: number; top: number; w?: number; children: React.ReactNode; tone?: "accent" | "ok" | "warn" }> = ({
  at, out, left, top, w = 440, children, tone = "accent",
}) => {
  const p = useIn(at, 0.5) * (1 - useIn(out ?? 999, 0.4));
  const col = tone === "ok" ? [C.okSoft, C.ok] : tone === "warn" ? ["#fff8e6", "#a06c00"] : [C.accentSoft, C.accent2];
  return (
    <div style={{ position: "absolute", left, top, width: w, background: col[0], color: col[1], borderRadius: 18, padding: "14px 20px",
      fontFamily: F.body, fontWeight: 700, fontSize: 26, lineHeight: 1.2, opacity: p, transform: `translateY(${(1 - p) * 14}px)` }}>
      {children}
    </div>
  );
};

/** Nota chica en mono (fuente de un dato, "datos de ejemplo"). */
export const Nota: React.FC<{ children: React.ReactNode; p?: number; style?: React.CSSProperties; color?: string }> = ({ children, p = 1, style, color = C.muted }) => (
  <div style={{ fontFamily: F.mono, fontSize: 18, color, opacity: p, letterSpacing: "0.02em", ...style }}>{children}</div>
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
        borderRadius: 12, maxWidth: 1600, textAlign: "center" }}>
        {texto}
      </div>
    </div>
  );
};

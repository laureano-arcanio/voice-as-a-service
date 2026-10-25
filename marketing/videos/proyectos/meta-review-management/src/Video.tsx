import React from "react";
import { Audio } from "@remotion/media";
import { AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { f, FPS } from "../../../src/comun/montaje";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { Cam, CRUCE, DIR, H, INICIO, Pt, SUBS, Toma, TOMAS, TOTAL, W } from "./timeline";

/**
 * App Review de Meta (whatsapp_business_management): una "grabación de pantalla" hecha con las capturas reales
 * del panel, con cámara suave, cursor y subtítulos en inglés. Sin locución ni música (pista de audio en silencio).
 */

const ease = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], { ...CLAMP, easing: EASE });

/** Cámara en el instante t: tramos suavizados entre keyframes; centrada y dentro de la captura. */
const camara = (cam: Cam[], t: number, size: [number, number]) => {
  let k = cam[0];
  for (let i = 1; i < cam.length; i++) {
    const a = cam[i - 1];
    const b = cam[i];
    if (t <= a.t) break;
    const p = ease(t, a.t, b.t);
    k = { t, x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, s: a.s + (b.s - a.s) * p };
  }
  const [iw, ih] = size;
  const hw = W / 2 / k.s;
  const hh = H / 2 / k.s;
  const x = iw <= hw * 2 ? iw / 2 : Math.min(Math.max(k.x, hw), iw - hw);
  const y = ih <= hh * 2 ? ih / 2 : Math.min(Math.max(k.y, hh), ih - hh);
  return { x, y, s: k.s };
};

const aPantalla = (c: { x: number; y: number; s: number }, x: number, y: number) => ({
  x: W / 2 + (x - c.x) * c.s,
  y: H / 2 + (y - c.y) * c.s,
});

const Puntero: React.FC<{ x: number; y: number; click: number | null; o: number }> = ({ x, y, click, o }) => (
  <div style={{ position: "absolute", left: x - 6, top: y - 3, opacity: o }}>
    {click !== null && click < 1 ? (
      <div style={{
        position: "absolute", left: -26, top: -28, width: 64, height: 64, borderRadius: 32,
        border: `4px solid ${C.accent}`, opacity: 1 - click, transform: `scale(${0.3 + click * 0.9})`,
      }} />
    ) : null}
    <svg width={36} height={44} viewBox="0 0 24 30" style={{
      filter: "drop-shadow(0 3px 4px rgba(11,18,32,.35))",
      transform: `scale(${click !== null && click < 0.35 ? 0.88 : 1})`, transformOrigin: "6px 3px",
    }}>
      <path d="M4 2 L4 24 L10 18 L14 27 L18 25 L14 16 L22 16 Z" fill="#ffffff" stroke={C.ink} strokeWidth={1.7} strokeLinejoin="round" />
    </svg>
  </div>
);

const Captura: React.FC<{ toma: Toma }> = ({ toma }) => {
  const t = useCurrentFrame() / FPS;
  const size = toma.size!;
  const c = camara(toma.cam!, t, size);
  const pos = aPantalla(c, 0, 0);

  // Cursor: tramos suavizados entre puntos (los de la captura siguen a la cámara)
  let cur: { x: number; y: number } | null = null;
  const pts = toma.cursor ?? [];
  const enPantalla = (p: Pt) => (p.pantalla ? { x: p.x, y: p.y } : aPantalla(c, p.x, p.y));
  if (pts.length && t >= pts[0].t) {
    cur = enPantalla(pts[0]);
    for (let i = 1; i < pts.length; i++) {
      if (t <= pts[i - 1].t) break;
      const a = enPantalla(pts[i - 1]);
      const b = enPantalla(pts[i]);
      const p = ease(t, pts[i - 1].t, pts[i].t);
      cur = { x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p };
    }
  }
  const ultimo = (toma.clicks ?? []).filter((k) => t >= k).pop();
  const click = ultimo === undefined ? null : (t - ultimo) / 0.5;
  const curO = pts.length ? interpolate(t, [pts[0].t, pts[0].t + 0.2], [0, 1], CLAMP) : 0;

  const pop = toma.popup;
  const popP = pop ? ease(t, pop.at, pop.at + 0.5) : 0;

  return (
    <AbsoluteFill style={{ background: toma.bg }}>
      <Img src={staticFile(`${DIR}/capturas/${toma.img}`)} style={{
        position: "absolute", left: pos.x, top: pos.y, width: size[0] * c.s, height: size[1] * c.s,
      }} />
      {pop ? (
        <div style={{
          position: "absolute", left: pop.x, top: pop.y + (1 - popP) * 24, width: 562 * pop.s, height: 670 * pop.s,
          opacity: popP, borderRadius: 10, overflow: "hidden", border: "1px solid #c3c8d0",
          boxShadow: "0 30px 80px rgba(11,18,32,.45), 0 4px 14px rgba(11,18,32,.25)",
        }}>
          <Img src={staticFile(`${DIR}/capturas/m06-popup-meta.png`)} style={{ width: "100%", height: "100%" }} />
        </div>
      ) : null}
      {cur ? <Puntero x={cur.x} y={cur.y} click={click} o={curO} /> : null}
    </AbsoluteFill>
  );
};

/** Placa de inicio y de cierre, en fondo oscuro con el logo blanco. */
const Placa: React.FC<{ fin?: boolean }> = ({ fin }) => {
  const t = useCurrentFrame() / FPS;
  const a = ease(t, 0.2, 1.0);
  const b = ease(t, 0.7, 1.5);
  return (
    <AbsoluteFill style={{ background: C.ink, alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 40 }}>
      <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ height: fin ? 92 : 76, opacity: a, transform: `translateY(${(1 - a) * 16}px)` }} />
      {fin ? (
        <div style={{ fontFamily: F.mono, fontSize: 40, color: C.accentOnDark, opacity: b }}>app.atentina.com.ar</div>
      ) : (
        <div style={{ textAlign: "center", opacity: b, transform: `translateY(${(1 - b) * 16}px)` }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 66, color: C.ctaInk, letterSpacing: -1 }}>
            WhatsApp Business Management
          </div>
          <div style={{ fontFamily: F.mono, fontSize: 36, color: C.accentOnDark, marginTop: 18 }}>whatsapp_business_management</div>
          <div style={{ fontFamily: F.body, fontSize: 28, color: C.ctaMuted, marginTop: 44 }}>
            Screen recording of the Atentina dashboard · app.atentina.com.ar
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

const Subtitulos: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  const s = SUBS.find((x) => t >= INICIO[x.toma] + x.de && t < INICIO[x.toma] + x.a);
  if (!s) return null;
  const de = INICIO[s.toma] + s.de;
  const a = INICIO[s.toma] + s.a;
  const o = interpolate(t, [de, de + 0.2, a - 0.2, a], [0, 1, 1, 0], CLAMP);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 44, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{
        background: "rgba(11,18,32,0.9)", color: "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 42, lineHeight: 1.3,
        padding: "14px 30px", borderRadius: 14, maxWidth: 1640, textAlign: "center",
      }}>
        {s.texto}
      </div>
    </div>
  );
};

export const MetaReviewManagementVideo: React.FC = () => (
  <AbsoluteFill style={{ background: C.ink }}>
    {TOMAS.map((toma, i) => {
      const len = f(toma.len + (i < TOMAS.length - 1 ? CRUCE : 0));
      return (
        <Sequence key={toma.id} from={f(INICIO[toma.id])} durationInFrames={len} name={toma.id}>
          <Fundido entra={i > 0}>
            {toma.img ? <Captura toma={toma} /> : <Placa fin={toma.id === "fin"} />}
          </Fundido>
        </Sequence>
      );
    })}
    <Subtitulos />
    {/* Sin sonido: un segundo de silencio en loop, para que el MP4 tenga pista de audio */}
    <Audio src={staticFile(`${DIR}/silencio.wav`)} loop />
  </AbsoluteFill>
);

const Fundido: React.FC<{ entra: boolean; children: React.ReactNode }> = ({ entra, children }) => {
  const frame = useCurrentFrame();
  const o = entra ? interpolate(frame, [0, f(CRUCE)], [0, 1], CLAMP) : 1;
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

export const DURACION = f(TOTAL);

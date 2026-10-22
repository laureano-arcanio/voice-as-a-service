import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";

// Conversación ilustrativa (call center genérico). Cada turno se escribe entre `at` y `at + 0.9` s.
const TURNOS = [
  { quien: "Agente", texto: "Buenas tardes, te habla Martín. ¿En qué te puedo ayudar?", at: 2.4 },
  { quien: "Cliente", texto: "Hola, me llegó la factura con un cargo que no reconozco.", at: 3.4 },
  { quien: "Agente", texto: "Lo reviso. ¿Me pasás tu número de cliente?", at: 4.4 },
  { quien: "Cliente", texto: "Sí, es el 48213.", at: 5.3 },
  { quien: "Agente", texto: "Es un cargo duplicado: te lo devolvemos en la próxima factura.", at: 6.0 },
] as const;
const TYPE = 0.9;

const DROP = 1.6; // el archivo cae en la zona
const DONE = 7.1; // termina la transcripción
const CLICK1 = 8.2; // clic en Descargar
const CLICK2 = 8.9; // clic en TXT

// Ventana: origen en (120, 250) de la escena, 1680 × 770
const W = 1680;
const H = 770;

/** Puntero del mouse, en coordenadas de la ventana. */
const Cursor: React.FC<{ x: number; y: number; press: number }> = ({ x, y, press }) => (
  <svg width={44} height={52} viewBox="0 0 22 26" style={{ position: "absolute", left: x, top: y, transform: `scale(${1 - 0.15 * press})`, transformOrigin: "0 0", filter: "drop-shadow(0 4px 6px rgba(11,18,32,.25))" }}>
    <path d="M2 2 L2 21 L7 16.5 L10.5 24 L14 22.5 L10.5 15 L17.5 15 Z" fill={C.ink} stroke="#fff" strokeWidth={1.6} strokeLinejoin="round" />
  </svg>
);

/** Ondas de los dos canales de la grabación (agente y cliente), con el cabezal que avanza. */
const Canales: React.FC<{ progreso: number }> = ({ progreso }) => {
  const N = 46;
  const fila = (seed: number, color: string, label: string) => (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ width: 84, fontFamily: F.mono, fontSize: 16, color: C.muted }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 3, height: 40, flex: 1 }}>
        {Array.from({ length: N }).map((_, i) => {
          // Turnos alternados: el agente habla en los tramos pares, el cliente en los impares
          const tramo = Math.floor((i / N) * 5);
          const habla = (tramo % 2 === 0) === (seed === 0);
          const h = habla ? 8 + 30 * Math.abs(Math.sin(i * 1.7 + seed * 2.1)) : 4;
          const pasado = i / N < progreso;
          return <div key={i} style={{ width: 5, height: h, borderRadius: 3, background: pasado ? color : C.line2 }} />;
        })}
      </div>
    </div>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {fila(0, C.accent, "Agente")}
      {fila(1, C.ink2, "Cliente")}
    </div>
  );
};

/** 1. El panel: se suelta la grabación, se transcribe por hablante y se descarga. */
export const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const win = usePop(0.1);
  const dropped = t >= DROP;
  const dropFlash = interpolate(t, [DROP - 0.3, DROP, DROP + 0.6], [0, 1, 0], CLAMP);
  const fileCard = usePop(DROP);
  const progreso = interpolate(t, [DROP + 0.4, DONE], [0, 1], CLAMP);
  const done = t >= DONE;
  const menu = useIn(CLICK1 + 0.05, 0.25) * (1 - useIn(CLICK2 + 0.2, 0.2));
  const toast = usePop(CLICK2 + 0.3);

  // Recorrido del puntero (coordenadas de la ventana)
  const kx = [0.3, DROP, 2.4, 7.3, CLICK1, CLICK1 + 0.3, CLICK2, 11];
  const xs = [1800, 250, 330, 330, 1530, 1500, 1490, 1490];
  const ys = [560, 250, 330, 330, 92, 150, 160, 160];
  const cx = interpolate(t, kx, xs, { ...CLAMP, easing: EASE });
  const cy = interpolate(t, kx, ys, { ...CLAMP, easing: EASE });
  const press = Math.max(
    interpolate(t, [DROP - 0.1, DROP, DROP + 0.1], [0, 1, 0], CLAMP),
    interpolate(t, [CLICK1 - 0.08, CLICK1, CLICK1 + 0.1], [0, 1, 0], CLAMP),
    interpolate(t, [CLICK2 - 0.08, CLICK2, CLICK2 + 0.1], [0, 1, 0], CLAMP),
  );
  const arrastra = t < DROP;

  return (
    <AbsoluteFill>
      <Headline eyebrow="Transcripción" text="Soltás la grabación" accent="y tenés el texto." />

      <div style={{ position: "absolute", left: 120, top: 250, width: W, height: H, transform: `scale(${win})`, transformOrigin: "50% 100%" }}>
        <div style={{ position: "absolute", inset: 0, background: "#fff", borderRadius: 28, border: `2px solid ${C.line}`, boxShadow: "0 24px 60px rgba(11,18,32,.14)", overflow: "hidden" }}>
          {/* barra de la ventana */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 20px", background: C.surface2, borderBottom: `2px solid ${C.line}`, height: 50, boxSizing: "border-box" }}>
            {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
            <Img src={staticFile("marca/atentina-logo.svg")} style={{ height: 24, marginLeft: 16 }} />
          </div>

          {/* encabezado */}
          <div style={{ position: "absolute", left: 36, top: 76, fontFamily: F.display, fontWeight: 700, fontSize: 34, color: C.ink }}>Transcripciones</div>
          <div style={{
            position: "absolute", right: 36, top: 70, display: "flex", alignItems: "center", gap: 10, borderRadius: 14, padding: "12px 24px",
            fontFamily: F.body, fontWeight: 700, fontSize: 24, background: done ? C.accent : C.surface2, color: done ? "#fff" : C.line2,
          }}>
            <svg viewBox="0 0 24 24" width={26} height={26}>
              <path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" fill="none" stroke={done ? "#fff" : C.line2} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Descargar
          </div>

          {/* zona para soltar */}
          <div style={{
            position: "absolute", left: 36, top: 150, width: 500, height: 230, borderRadius: 22, boxSizing: "border-box",
            border: `3px dashed ${dropFlash > 0.05 ? C.accent : C.line2}`, background: dropFlash > 0.05 ? C.accentSoft : "#fbfcfe",
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10,
          }}>
            <Icon name="upload" size={46} color={C.accent} />
            <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 26, color: C.ink }}>Soltá la grabación acá</div>
            <div style={{ fontFamily: F.mono, fontSize: 17, color: C.muted }}>wav · mp3 · ogg · hasta 25 MB</div>
          </div>

          {/* el archivo cargado */}
          <div style={{
            position: "absolute", left: 36, top: 410, width: 500, borderRadius: 22, border: `2px solid ${C.line}`, padding: "20px 22px", boxSizing: "border-box",
            transform: `scale(${dropped ? fileCard : 0})`, transformOrigin: "50% 0%",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 46, height: 46, borderRadius: 12, background: C.accentSoft, display: "grid", placeItems: "center" }}>
                <Icon name="speaker" size={26} color={C.accent} />
              </div>
              <div>
                <div style={{ fontFamily: F.mono, fontSize: 21, color: C.ink }}>llamada-0142.wav</div>
                <div style={{ fontFamily: F.body, fontSize: 18, color: C.muted }}>3:12 · estéreo, un canal por lado</div>
              </div>
            </div>
            <div style={{ marginTop: 16 }}><Canales progreso={progreso} /></div>
            <div style={{ marginTop: 16, height: 8, borderRadius: 4, background: C.surface2, overflow: "hidden" }}>
              <div style={{ width: `${progreso * 100}%`, height: "100%", background: done ? C.ok : C.accent }} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, fontFamily: F.body, fontWeight: 600, fontSize: 20, color: done ? C.ok : C.accent }}>
              {done ? <><Icon name="check" size={22} color={C.ok} /> Transcripción lista · 2 hablantes</> : "Transcribiendo…"}
            </div>
          </div>

          {/* la transcripción */}
          <div style={{ position: "absolute", left: 590, top: 150, width: 1054, display: "flex", flexDirection: "column", gap: 14 }}>
            {TURNOS.map((x) => {
              const p = interpolate(t, [x.at - 0.15, x.at + 0.1], [0, 1], CLAMP);
              const n = Math.floor(interpolate(t, [x.at, x.at + TYPE], [0, x.texto.length], CLAMP));
              const escribiendo = t >= x.at && t < x.at + TYPE;
              const agente = x.quien === "Agente";
              return (
                <div key={x.texto} style={{
                  display: "flex", alignItems: "flex-start", gap: 18, opacity: p, transform: `translateY(${(1 - p) * 12}px)`,
                  padding: "14px 18px", borderRadius: 16, background: escribiendo ? C.bg2 : "transparent", border: `2px solid ${escribiendo ? C.line : "transparent"}`,
                }}>
                  <div style={{
                    width: 112, flexShrink: 0, textAlign: "center", borderRadius: 999, padding: "6px 0", fontFamily: F.body, fontWeight: 700, fontSize: 20,
                    background: agente ? C.accentSoft : C.surface2, color: agente ? C.accent : C.ink2,
                  }}>
                    {x.quien}
                  </div>
                  <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.35, color: C.ink, paddingTop: 2 }}>
                    {x.texto.slice(0, n)}
                    {escribiendo ? <span style={{ color: C.accent }}>▍</span> : null}
                  </div>
                </div>
              );
            })}
          </div>

          {/* aviso de descarga */}
          <div style={{
            position: "absolute", right: 36, bottom: 30, display: "flex", alignItems: "center", gap: 12, borderRadius: 16, padding: "14px 22px",
            background: C.ink, color: "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 22, transform: `scale(${toast})`, transformOrigin: "100% 100%",
          }}>
            <Icon name="check" size={24} color="#5ee49a" />
            <span style={{ fontFamily: F.mono, fontSize: 20 }}>llamada-0142.txt</span> descargado
          </div>
        </div>

        {/* menú de formatos */}
        <div style={{
          position: "absolute", right: 36, top: 132, width: 250, background: "#fff", borderRadius: 16, border: `2px solid ${C.line}`,
          boxShadow: "0 18px 40px rgba(11,18,32,.16)", padding: 8, opacity: menu, transform: `translateY(${(1 - menu) * -8}px)`,
        }}>
          {[{ f: "TXT", d: "texto plano" }, { f: "JSON", d: "por hablante" }].map((o, i) => (
            <div key={o.f} style={{
              display: "flex", alignItems: "baseline", gap: 12, padding: "10px 14px", borderRadius: 10,
              background: i === 0 && t > CLICK2 - 0.3 ? C.accentSoft : "transparent",
            }}>
              <span style={{ fontFamily: F.mono, fontSize: 21, color: C.ink, width: 64 }}>{o.f}</span>
              <span style={{ fontFamily: F.body, fontSize: 19, color: C.muted }}>{o.d}</span>
            </div>
          ))}
        </div>

        {/* archivo arrastrado y puntero */}
        {arrastra ? (
          <div style={{
            position: "absolute", left: cx + 18, top: cy + 30, display: "flex", alignItems: "center", gap: 10, background: "#fff", borderRadius: 14,
            border: `2px solid ${C.accent}`, padding: "10px 16px", boxShadow: "0 14px 30px rgba(36,86,230,.25)", fontFamily: F.mono, fontSize: 19, color: C.ink,
            opacity: interpolate(t, [0.3, 0.5, DROP - 0.1, DROP], [0, 1, 1, 0], CLAMP),
          }}>
            <Icon name="speaker" size={22} color={C.accent} /> llamada-0142.wav
          </div>
        ) : null}
        <div style={{ opacity: interpolate(t, [0.3, 0.5, 10.4, 10.8], [0, 1, 1, 0], CLAMP) }}>
          <Cursor x={cx} y={cy} press={press} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

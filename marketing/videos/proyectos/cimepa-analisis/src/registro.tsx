import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { CodeLine, CodeWindow, Ok } from "../../../src/comun/code";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// c6 (v2, paula): "Y por API, su sistema recibe todo:" 0,1 · "el audio de la llamada," 2,4 · "la transcripción," ~3,5 ·
// "el resumen y el resultado." ~4,3–5,67 · "Inferencia propia, en Argentina." 5,93–7,43
// En v2 el panel y la transcripción de ejemplo pasaron a la escena entra: acá va lo que recibe su sistema (PDF, hoja 4).
const M6 = { api: 0.1, audio: 2.4, transcripcion: 3.5, resumen: 4.3, datos: 5.0, inferencia: 5.93 };

type Quien = "IA" | "Cliente" | "Persona";
const COLOR: Record<Quien, string> = { IA: C.accent, Cliente: C.muted, Persona: C.ok };
// Barras de la grabación: el tramo de la IA, la transferencia y el de la persona (forma determinística)
const BARRAS = Array.from({ length: 104 }, (_, i) => ({
  h: 0.25 + 0.75 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.37)),
  q: (i < 42 ? (i % 12 < 6 ? "IA" : "Cliente") : i < 47 ? null : i % 12 < 7 ? "Persona" : "Cliente") as Quien | null,
}));
// Lo que recibe, por cada llamada (PDF, hoja 4)
const RECIBE = [
  { k: "Audio", x: "de toda la llamada, si la grabación está activa.", at: M6.audio },
  { k: "Transcripción", x: "turno por turno, con quién habló (IA o persona) y cuándo.", at: M6.transcripcion },
  { k: "Resumen y resultado", x: "y los datos capturados: “volver a llamar el jueves a las 15”.", at: M6.resumen },
  { k: "Datos de la llamada", x: "números, duración, quién atendió y transferencias.", at: M6.datos },
];
const API = `{ "outcome": { "label": "Derivada", "goal": true },
  "fields": [
    { "name": "volver_a_llamar",
      "value": "jueves 15 h" } ],
  "messages": [
    { "role": "assistant",
      "text": "Hola, gracias por llamar…",
      "recording": 1 }, … ],
  "call": { "duration_seconds": 252 } }`;

/** 5. Todo queda registrado: por API su sistema recibe audio, transcripción, resumen y resultado; inferencia propia. */
export const Registro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.c6 + s;
  const card = useIn(v(0.1), 0.6);
  const api = useIn(v(M6.api + 0.3), 0.6);
  const play = interpolate(t, [v(M6.audio), v(M6.audio + 1.4)], [0, 1], CLAMP);
  const items = RECIBE.map((x) => useIn(v(x.at - 0.1), 0.5));
  const banda = useIn(v(M6.inferencia - 0.1), 0.6);
  const chips = [usePop(v(M6.inferencia + 0.3)), usePop(v(M6.inferencia + 0.5)), usePop(v(M6.inferencia + 0.7))];
  return (
    <AbsoluteFill>
      <Headline eyebrow="Todo queda registrado" text="Por cada llamada, su sistema recibe" accent="todo por API." />

      <div style={{
        position: "absolute", left: 120, top: 262, width: 1000, height: 600, boxSizing: "border-box", padding: "26px 32px", borderRadius: 24,
        background: "#fff", border: `2px solid ${C.line}`, boxShadow: shadowCard, opacity: card, transform: `translateY(${(1 - card) * 30}px)`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>LO QUE RECIBE, POR CADA LLAMADA</div>
        <div style={{ display: "flex", alignItems: "center", gap: 2, height: 66, marginTop: 14 }}>
          {BARRAS.map((b, i) => (
            <div key={i} style={{
              width: 6, marginRight: 1, height: b.q ? 58 * b.h : 2, borderRadius: 3, background: b.q ? COLOR[b.q] : C.line2,
              opacity: i / BARRAS.length <= play ? 1 : 0.22,
            }} />
          ))}
        </div>
        <div style={{ display: "flex", gap: 22, marginTop: 6, fontFamily: F.mono, fontSize: 16, color: C.muted }}>
          {(["IA", "Persona", "Cliente"] as Quien[]).map((q) => (
            <span key={q} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: COLOR[q] }} />{q === "Persona" ? "Persona de su equipo" : q}
            </span>
          ))}
        </div>
        <div style={{ marginTop: 18, borderTop: `2px solid ${C.line}` }}>
          {RECIBE.map((x, i) => (
            <div key={x.k} style={{
              display: "flex", alignItems: "center", gap: 18, height: 84, borderBottom: i < RECIBE.length - 1 ? `2px solid ${C.line}` : "none",
              opacity: 0.2 + 0.8 * items[i], transform: `translateX(${(1 - items[i]) * -16}px)`,
            }}>
              <Icon name="check" size={32} color={items[i] > 0.5 ? C.accent : C.line2} />
              <div style={{ fontFamily: F.body, fontSize: 25, color: C.ink2, lineHeight: 1.25 }}>
                <b style={{ color: C.ink }}>{x.k}</b> {x.x}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ position: "absolute", left: 1170, top: 262, width: 630, opacity: api, transform: `translateX(${(1 - api) * 30}px)` }}>
        <CodeWindow tab="su sistema" method="GET" path="/api/v1/calls/{id}" status={<Ok>200</Ok>} fontSize={18} minHeight={466}>
          {API.split("\n").map((l, i) => <CodeLine key={i} line={l} />)}
        </CodeWindow>
      </div>

      <div style={{
        position: "absolute", left: 120, right: 120, top: 888, height: 84, boxSizing: "border-box", padding: "0 30px", borderRadius: 20,
        background: C.ink, display: "flex", alignItems: "center", gap: 22, opacity: banda, transform: `translateY(${(1 - banda) * 20}px)`,
      }}>
        <span style={{ fontFamily: F.mono, fontSize: 19, letterSpacing: "0.08em", color: C.accentOnDark, whiteSpace: "nowrap" }}>INFERENCIA PROPIA · SERVIDORES EN ARGENTINA</span>
        <span style={{ flex: 1 }} />
        {["Reconocimiento de voz", "Modelo de lenguaje", "Voz"].map((x, i) => (
          <span key={x} style={{
            borderRadius: 999, padding: "8px 18px", background: "#16213a", border: "2px solid #23304d", fontFamily: F.body, fontWeight: 600, fontSize: 21,
            color: C.ctaInk, whiteSpace: "nowrap", transform: `scale(${chips[i]})`, opacity: Math.min(1, chips[i] * 1.5),
          }}>{x}</span>
        ))}
      </div>

      <Pie hoja="4 / 5" fuente="Los campos de la respuesta son los de la API; los valores, de ejemplo." />
    </AbsoluteFill>
  );
};

// c7 (v2, paula): "Su agente:" 0,13 · "tres vías," ~0,8 · "para definir en una charla técnica." ~1,4–3,17 · "En tiempo real," 3,47 ·
// "por SIP," ~4,35 · "o nuestro agente," ~4,85 · "con su contexto y su modelo." ~5,8–7,3
const M7 = { vias: 0.8, real: 3.47, sip: 4.35, nuestro: 4.85, fin: 9.5 };
// Las tres vías de la hoja 4 del PDF
const VIAS = [
  {
    n: 1, titulo: "En tiempo real, por WebRTC", at: M7.real, hasta: M7.sip,
    texto: "Su agente se une a la llamada como un participante más (estándar LiveKit), con un token por llamada: recibe el audio y responde con el suyo, en streaming bidireccional.",
    ej: "Si el agente lo construyen ustedes (LiveKit Agents, Pipecat o propio).",
  },
  {
    n: 2, titulo: "Por SIP", at: M7.sip, hasta: M7.nuestro,
    texto: "Las llamadas de la línea se enrutan a la dirección SIP de su plataforma, y sus salientes salen por la nuestra con el número de la empresa.",
    ej: "Si su agente vive en una plataforma de voz que ya habla SIP.",
  },
  {
    n: 3, titulo: "Nuestro agente, con lo suyo", at: M7.nuestro, hasta: M7.fin,
    texto: "Ustedes ponen el contexto, las reglas y las herramientas (webhooks a su sistema) y, si quieren, su propio modelo de lenguaje con su API key.",
    ej: "Si todavía no tienen la voz resuelta o quieren arrancar rápido.",
  },
];

/** 6. Su agente: tres vías para definir en una charla técnica. */
export const Agente: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.c7 + s;
  const ins = VIAS.map((_, i) => useIn(v(M7.vias + i * 0.17), 0.5));
  const ons = VIAS.map((x) => interpolate(t, [v(x.at - 0.1), v(x.at + 0.2), v(x.hasta - 0.1), v(x.hasta + 0.2)], [0, 1, 1, x.hasta === M7.fin ? 1 : 0.35], CLAMP));
  const nota = useIn(v(2.0), 0.6);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Integración de su agente" text="Su agente en la línea de la empresa:" accent="la vía la elegimos juntos." size={58} />

      {VIAS.map((x, i) => {
        const on = ons[i];
        return (
          <div key={x.n} style={{
            position: "absolute", left: 120 + i * 570, top: 290, width: 540, height: 470, boxSizing: "border-box", padding: "30px 32px",
            borderRadius: 24, background: on > 0.5 ? C.accentSoft : "#fff", border: `2px solid ${on > 0.5 ? C.accent : C.line}`,
            boxShadow: on > 0.05 ? `0 0 0 ${8 * on}px rgba(36,86,230,.10), ${shadowCard}` : shadowCard,
            opacity: ins[i], transform: `translateY(${(1 - ins[i]) * 30}px) scale(${1 + 0.02 * on})`,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{
                width: 52, height: 52, borderRadius: 26, display: "flex", alignItems: "center", justifyContent: "center",
                background: on > 0.5 ? C.accent : C.accentSoft, color: on > 0.5 ? "#fff" : C.accent, fontFamily: F.display, fontWeight: 800, fontSize: 28,
              }}>{x.n}</div>
              {i === 0 ? <Icon name="web" size={44} color={C.accent} /> : i === 1 ? <Icon name="phone" size={42} color={C.accent} /> : <AgenteLogo size={58} />}
            </div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 33, lineHeight: 1.1, color: on > 0.5 ? C.accent : C.ink, marginTop: 18, whiteSpace: "nowrap" }}>{x.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 22, lineHeight: 1.4, color: C.ink2, marginTop: 14 }}>{x.texto}</div>
            <div style={{
              position: "absolute", left: 32, right: 32, bottom: 26, borderTop: `2px solid ${C.line}`, paddingTop: 12,
              fontFamily: F.body, fontSize: 19, lineHeight: 1.35, color: C.muted,
            }}>{x.ej}</div>
          </div>
        );
      })}

      <div style={{
        position: "absolute", left: 120, right: 120, top: 800, boxSizing: "border-box", padding: "22px 30px", borderRadius: 20,
        background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.accent}`, boxShadow: shadowCard,
        fontFamily: F.body, fontSize: 25, lineHeight: 1.4, color: C.ink2, opacity: nota, transform: `translateY(${(1 - nota) * 20}px)`,
      }}>
        <b style={{ color: C.ink }}>En las tres, la llamada pasa por la plataforma:</b> el número, las transferencias, la grabación y la transcripción funcionan igual, hable quien hable.
      </div>

      <Pie hoja="4 / 5" fuente="La vía se define en la charla técnica, según con qué esté hecho su agente." />
    </AbsoluteFill>
  );
};

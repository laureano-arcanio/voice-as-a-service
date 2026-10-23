import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop, Wave } from "../../../src/comun/ui";
import { AT } from "./timeline";

/** Pie de página como el del PDF: "Atentina · Propuesta técnica para CIMEPA S.A." y la hoja. */
export const Pie: React.FC<{ fuente?: string; hoja: string }> = ({ fuente, hoja }) => {
  const o = useIn(0.6, 0.6);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · PROPUESTA TÉCNICA PARA CIMEPA S.A. · {hoja}</span>
    </div>
  );
};

// Las cuatro cifras de la portada del PDF (hoja 1)
const STATS = [
  { b: "3 o más", t: "números argentinos" },
  { b: "3 o más", t: "llamadas simultáneas" },
  { b: "Nada", t: "que instalar" },
  { b: "Todas", t: "grabadas y transcriptas" },
];

/** 0. Intro oscura: la portada del PDF. */
export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.45, 0.7);
  // "todo grabado y transcripto." arranca a ~2,75 s de c1
  const remate = useIn(AT.c1 + 2.8, 0.6);
  const sub = useIn(1.3, 0.6);
  const idx = [usePop(1.9), usePop(2.1), usePop(2.3), usePop(2.5)];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 110, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 320 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 236, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PROPUESTA TÉCNICA · CIMEPA S.A. · OCTUBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 310, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 84,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Un número de la empresa<br />para su equipo y su IA,<br />
        <span style={{ color: C.accentOnDark, opacity: 0.25 + 0.75 * remate }}>todo grabado y transcripto.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 618, textAlign: "center", fontFamily: F.body, fontSize: 34, color: C.ctaMuted, opacity: sub }}>
        Telefonía con IA para un equipo remoto
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 740, display: "flex", justifyContent: "center", gap: 18 }}>
        {STATS.map((s, i) => (
          <div key={s.t} style={{
            display: "flex", alignItems: "baseline", gap: 14, borderRadius: 18, padding: "18px 26px", background: "#16213a",
            border: "2px solid #23304d", transform: `scale(${idx[i]})`, opacity: Math.min(1, idx[i] * 1.5),
          }}>
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.accentOnDark, whiteSpace: "nowrap" }}>{s.b}</span>
            <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 26, color: C.ctaInk, whiteSpace: "nowrap" }}>{s.t}</span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/** Flechas de ida y vuelta (transferir en los dos sentidos). */
const Ida: React.FC<{ size: number }> = ({ size }) => (
  <svg viewBox="0 0 24 24" width={size} height={size}>
    <path d="M4 8h14M14 4l4 4-4 4M20 16H6M10 12l-4 4 4 4" fill="none" stroke={C.accent} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

type Pedido = { k: string; titulo: string; cita: string; como: React.ReactNode; at: number; icono: React.ReactNode };
// Los cuatro pedidos del PDF (hoja 1, "Lo que nos pidieron, en sus palabras"), con su "Cómo"
// v2: c2 (paula) "En CIMEPA nos pidieron cuatro cosas." y cada pedido en su línea (pablo)
const PEDIDOS: Pedido[] = [
  {
    k: "1 · SU EQUIPO", titulo: "Su equipo remoto llama sin teléfono", at: AT.c2a + 0.05,
    cita: "Que una persona haga y reciba llamadas desde su computadora o celular",
    como: <><b>Cómo:</b> llaman desde una app web con la agenda y el número de la empresa. Lo que les deriva la IA les suena en su celular.</>,
    icono: <Icon name="web" size={40} color={C.accent} />,
  },
  {
    k: "2 · SU ASISTENTE DE IA", titulo: "Su asistente de IA llama y atiende", at: AT.c2b + 0.05,
    cita: "Conectar un asistente propio que gestione la conversación de voz en tiempo real",
    como: <><b>Cómo:</b> atiende las entrantes y hace salientes de seguimiento por API. La vía para conectar el suyo, en una charla técnica.</>,
    icono: <AgenteLogo size={56} />,
  },
  {
    k: "3 · TRANSFERENCIAS", titulo: "Transferir entre la IA y una persona", at: AT.c2c + 0.05,
    cita: "¿Permiten transferir llamadas tanto de IA a persona como de persona a IA?",
    como: <><b>Sí, en los dos sentidos:</b> la IA deriva al empleado con un resumen, y el empleado le devuelve la llamada con el contexto.</>,
    icono: <Ida size={40} />,
  },
  {
    k: "4 · REGISTRO", titulo: "Todo grabado y transcripto, por API", at: AT.c2d + 0.05,
    cita: "Que las conversaciones queden grabadas",
    como: <><b>Cómo:</b> toda la llamada, hable la IA o una persona, en un solo historial: audio, transcripción y resultado, en el panel y por API.</>,
    icono: <Wave n={5} h={34} color={C.accent} />,
  },
];

/** 1. Lo que nos pidieron: cuatro tarjetas, una por línea de la locución. */
export const Pedido: React.FC = () => {
  const p = PEDIDOS.map((x) => useIn(x.at, 0.6));
  const como = PEDIDOS.map((x) => useIn(x.at + 1.1, 0.6));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que nos pidieron" text="En sus palabras," accent="y cómo lo resolvemos." />
      {PEDIDOS.map((x, i) => {
        const left = i % 2 === 0 ? 120 : 975;
        const top = i < 2 ? 262 : 630;
        return (
          <div key={x.k} style={{
            position: "absolute", left, top, width: 825, height: 340, boxSizing: "border-box", padding: "26px 36px",
            background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.accent}`, borderRadius: 24, boxShadow: shadowCard,
            opacity: p[i], transform: `translateY(${(1 - p[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>{x.k}</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.01em", marginTop: 6, whiteSpace: "nowrap" }}>{x.titulo}</div>
            <div style={{ fontFamily: F.body, fontStyle: "italic", fontSize: 25, lineHeight: 1.35, color: C.ink2, marginTop: 14, width: 640 }}>“{x.cita}”</div>
            <div style={{
              position: "absolute", right: 30, top: 24, width: 76, height: 76, borderRadius: 38, background: C.accentSoft,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>{x.icono}</div>
            <div style={{
              position: "absolute", left: 36, right: 36, bottom: 22, borderTop: `2px solid ${C.line}`, paddingTop: 12,
              fontFamily: F.body, fontSize: 23, lineHeight: 1.32, color: C.accent2, opacity: como[i],
            }}>
              {x.como}
            </div>
          </div>
        );
      })}
      <Pie hoja="1 / 5" fuente="Los pedidos, textuales del WhatsApp del 22-oct-2026." />
    </AbsoluteFill>
  );
};

/** 7. Cierre: solo la pregunta, con el contacto de Atentina chico abajo. */
export const Cierre: React.FC = () => {
  const line = useIn(0.3, 0.7);
  const contacto = useIn(1.2, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 100, lineHeight: 1.1, color: C.ctaInk, opacity: line, transform: `translateY(${(1 - line) * 24}px)`, letterSpacing: "-0.02em",
      }}>
        ¿Agendamos la<br /><span style={{ color: C.accentOnDark }}>charla técnica?</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 930, display: "flex", justifyContent: "center", alignItems: "center", gap: 28, opacity: contacto }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 150 }} />
        <div style={{ fontFamily: F.mono, fontSize: 24, color: C.ctaMuted }}>atentina.com.ar · 0800-220-1233</div>
      </div>
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { C, F, shadowCard } from "../../../src/comun/theme";
import { Headline, useIn, usePop } from "../../../src/comun/ui";
import { AT, en } from "./timeline";

/** Pie de página como el del PDF: "Atentina · Propuesta técnica para Axioma IT Solutions" y la hoja. */
export const Pie: React.FC<{ fuente?: string; hoja: string }> = ({ fuente, hoja }) => {
  const o = useIn(0.6, 0.6);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · PROPUESTA TÉCNICA PARA AXIOMA IT SOLUTIONS · {hoja}</span>
    </div>
  );
};

// "Atentina, en cuatro datos" (PDF, hoja 1)
const DATOS4 = [
  { b: "41 voces", t: "con acento argentino" },
  { b: "0,87 s", t: "de respuesta en su llamada a la demo" },
  { b: "4 en 1", t: "número, agente, voces y WhatsApp" },
  { b: "1 API", t: "llamadas, campañas, contactos y motores" },
];

/** 0. Intro oscura: la portada del PDF. */
export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.45, 0.7);
  const remate = useIn(en("a1", "Odoo") - 0.1, 0.6);
  const sub = useIn(1.3, 0.6);
  const idx = [usePop(1.9), usePop(2.1), usePop(2.3), usePop(2.5)];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 110, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 320 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 236, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PROPUESTA TÉCNICA · AXIOMA IT SOLUTIONS · OCTUBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 316, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 88,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Sumen voz a lo que ya venden:<br />
        <span style={{ color: C.accentOnDark, opacity: 0.25 + 0.75 * remate }}>Odoo, agentes de IA y turnos.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 540, textAlign: "center", fontFamily: F.body, fontSize: 34, color: C.ctaMuted, opacity: sub }}>
        Voz con IA para un integrador, por API
      </div>
      <div style={{ position: "absolute", left: 160, right: 160, top: 690, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 22 }}>
        {DATOS4.map((s, i) => (
          <div key={s.b} style={{
            borderRadius: 20, padding: "24px 28px", background: "#16213a", border: "2px solid #23304d",
            transform: `scale(${idx[i]})`, opacity: Math.min(1, idx[i] * 1.5),
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 52, color: C.accentOnDark, whiteSpace: "nowrap", lineHeight: 1.05 }}>{s.b}</div>
            <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.ctaInk, marginTop: 10, lineHeight: 1.3 }}>{s.t}</div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

type Dato = { cifra: string; texto: string; fuente: string; frag: string };
// "Lo que ya hacen bien" (PDF, hoja 1); cada tarjeta entra con su parte de a2
const DATOS: Dato[] = [
  { cifra: "+100", texto: "proyectos entregados, con equipo de ingenieros de la UTN FRBA", fuente: "axiomait.com", frag: "más de cien" },
  { cifra: "Silver", texto: "partner de Odoo: 30 referencias y 97 % de retención; partner de Microsoft", fuente: "ficha de partner en odoo.com", frag: "con clientes" },
  { cifra: "5,0", texto: "de calificación en Google (17 reseñas) y en Clutch", fuente: "Google Maps y Clutch", frag: "cinco estrellas" },
  { cifra: "ISO 9001", texto: "en desarrollo de software a medida, certificada por Bureau Veritas", fuente: "axiomait.com", frag: "estrellas" },
];

/** 1. Lo que ya hacen bien: las cuatro cifras de la hoja 1. */
export const Bien: React.FC = () => {
  const ins = DATOS.map((d) => useIn(en("a2", d.frag) - 0.15, 0.6));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que ya hacen bien" text="Más de cien proyectos, y clientes" accent="que se quedan." />
      {DATOS.map((d, i) => {
        const x = i % 2 === 0 ? 120 : 975;
        const y = i < 2 ? 262 : 620;
        const p = ins[i];
        return (
          <div key={d.cifra} style={{
            position: "absolute", left: x, top: y, width: 825, height: 320, boxSizing: "border-box", padding: "34px 40px",
            background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.ok}`, borderRadius: 24, boxShadow: shadowCard,
            opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 76, lineHeight: 1.05, color: C.ink, letterSpacing: "-0.015em" }}>{d.cifra}</div>
            <div style={{ fontFamily: F.body, fontSize: 30, lineHeight: 1.35, color: C.ink2, marginTop: 16 }}>{d.texto}</div>
            <div style={{ position: "absolute", left: 40, bottom: 26, fontFamily: F.mono, fontSize: 18, color: C.muted }}>{d.fuente.toUpperCase()}</div>
          </div>
        );
      })}
      <Pie hoja="1 / 6" fuente="Leídos el 22-oct-2026." />
    </AbsoluteFill>
  );
};

type Linea = { k: string; titulo: string; texto: string; oportunidad: string; at: number };
// "Dónde encaja Atentina" (PDF, hoja 2): una tarjeta por línea de Axioma, cada una con su línea de lucas (b1 a b4)
const LINEAS: Linea[] = [
  {
    k: "ODOO Y CRM", titulo: "Leads de formularios, Meta Ads y el Kit 4.0", at: AT.b1,
    texto: "Varios formularios prometen respuesta en menos de 24 horas, y los cupos del Kit 4.0 van por orden de llegada.",
    oportunidad: "el CRM dispara la llamada; el agente califica, agenda el diagnóstico y deja el resultado.",
  },
  {
    k: "SOLUCIONES IA Y N8N", titulo: "Agentes de IA a medida, en 4 a 8 semanas", at: AT.b2,
    texto: "Ya los diseñan para ventas, soporte y datos, e integran con n8n. La voz telefónica es el canal que se suma.",
    oportunidad: "el mismo agente, también por teléfono y WhatsApp, con una API en lugar de armar telefonía.",
  },
  {
    k: "TODOTURNOS", titulo: "Recordatorios por WhatsApp: 70 % menos ausencias", at: AT.b3,
    texto: "En Sanatorio Santa Rosa. En Badent, antes, los turnos se confirmaban llamando a mano.",
    oportunidad: "una llamada de confirmación para quien no lee el WhatsApp, con reprogramación.",
  },
  {
    k: "SOPORTE ODOO", titulo: "Planes con atención telefónica y guardia 24/7", at: AT.b4,
    texto: "Los tres planes de soporte incluyen teléfono y guardia pasiva, también los fines de semana.",
    oportunidad: "un primer nivel que atiende a toda hora, toma el caso y lo deja cargado para el consultor.",
  },
];

/** 2. Dónde encaja Atentina: cuatro tarjetas, una por línea de la locución de lucas. */
export const Lineas: React.FC = () => {
  const p = LINEAS.map((x) => useIn(x.at - 0.1, 0.6));
  const op = LINEAS.map((x) => useIn(x.at + 1.4, 0.6));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Dónde encaja Atentina" text="Voz para cada línea que ya venden," accent="sin montar telefonía." size={56} />
      {LINEAS.map((x, i) => {
        const left = i % 2 === 0 ? 120 : 975;
        const top = i < 2 ? 262 : 630;
        return (
          <div key={x.k} style={{
            position: "absolute", left, top, width: 825, height: 340, boxSizing: "border-box", padding: "26px 36px",
            background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.accent}`, borderRadius: 24, boxShadow: shadowCard,
            opacity: p[i], transform: `translateY(${(1 - p[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>{x.k}</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.01em", marginTop: 6 }}>{x.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 24, lineHeight: 1.35, color: C.ink2, marginTop: 12 }}>{x.texto}</div>
            <div style={{
              position: "absolute", left: 36, right: 36, bottom: 22, borderTop: `2px solid ${C.line}`, paddingTop: 12,
              fontFamily: F.body, fontSize: 23, lineHeight: 1.32, color: C.accent2, opacity: op[i],
            }}>
              <b>Oportunidad:</b> {x.oportunidad}
            </div>
          </div>
        );
      })}
      <Pie hoja="2 / 6" fuente="axiomait.com (Odoo, Soluciones IA, Kit 4.0, soporte y casos), leído el 22-oct-2026." />
    </AbsoluteFill>
  );
};

// "Cómo se pone en marcha" (PDF, hoja 6)
const OFERTA = [
  { k: "HOY, SIN HABLAR CON NADIE", b: "Acceso para probar", frag: "Pueden probarlo",
    t: "Registro en atentina.com.ar: panel, API keys, agentes, las 41 voces y llamadas desde el navegador." },
  { k: "SI LA QUIEREN", b: "Demo técnica, 30 min", frag: "una demo",
    t: "La API en vivo: se crea un lead de prueba, se programa la campaña y suena el celular de Axel." },
  { k: "PARA DECIDIR", b: "Piloto de 30 días", frag: "un piloto",
    t: "El llamador del CRM con los leads de Axioma, con un número argentino y soporte directo." },
];
const DESPUES = ["TodoTurnos", "Soporte Odoo", "Clientes Odoo", "Acuerdo de canal"];

/** 6. Puesta en marcha: probar hoy, demo técnica y piloto de 30 días; después, revenderlo. */
export const Marcha: React.FC = () => {
  const ins = OFERTA.map((o) => useIn(en("a9", o.frag) - 0.15, 0.6));
  const tira = useIn(en("a9", "con sus leads"), 0.6);
  const chips = DESPUES.map((_, i) => usePop(en("a9", "con sus leads") + 0.3 + i * 0.15));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Cómo se pone en marcha" text="Primero lo prueban solos." accent="Después, 30 días con sus leads." size={56} />
      <div style={{ position: "absolute", left: 120, right: 120, top: 270, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 30 }}>
        {OFERTA.map((o, i) => (
          <div key={o.k} style={{
            height: 340, boxSizing: "border-box", padding: "32px 34px", borderRadius: 26, boxShadow: shadowCard,
            background: i === 0 ? `linear-gradient(180deg, ${C.accentSoft}, #fff 85%)` : "#fff",
            border: i === 0 ? `3px solid ${C.accent}` : `2px solid ${C.line}`,
            opacity: ins[i], transform: `translateY(${(1 - ins[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: i === 0 ? C.accent : C.muted }}>{o.k}</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, lineHeight: 1.1, color: C.accent, marginTop: 14 }}>{o.b}</div>
            <div style={{ fontFamily: F.body, fontSize: 28, lineHeight: 1.4, color: C.ink2, marginTop: 18 }}>{o.t}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 700, opacity: tira }}>
        <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted }}>DESPUÉS DEL PILOTO: REVENDERLO A SUS CLIENTES</div>
        <div style={{ display: "flex", gap: 18, marginTop: 18 }}>
          {DESPUES.map((d, i) => (
            <div key={d} style={{
              fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, background: "#fff", border: `2px solid ${C.line2}`,
              borderRadius: 999, padding: "14px 30px", transform: `scale(${chips[i]})`,
            }}>{d}</div>
          ))}
        </div>
      </div>
      <Pie hoja="6 / 6" fuente="Probar el acceso no tiene costo." />
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
        ¿Agendamos una<br /><span style={{ color: C.accentOnDark }}>demo técnica?</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 930, display: "flex", justifyContent: "center", alignItems: "center", gap: 28, opacity: contacto }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 150 }} />
        <div style={{ fontFamily: F.mono, fontSize: 24, color: C.ctaMuted }}>atentina.com.ar · 0800-220-1233</div>
      </div>
    </AbsoluteFill>
  );
};

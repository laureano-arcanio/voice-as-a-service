import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { C, F, shadowCard } from "../../../src/comun/theme";
import { Headline, useIn, usePop } from "../../../src/comun/ui";
import { AT, en } from "./timeline";

/** Pie de página como el del PDF: "Atentina · Propuesta de alianza para Zennon BI" y la hoja. */
export const Pie: React.FC<{ fuente?: string; hoja: string }> = ({ fuente, hoja }) => {
  const o = useIn(0.6, 0.6);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · PROPUESTA DE ALIANZA PARA ZENNON BI · {hoja}</span>
    </div>
  );
};

// "Atentina, en cuatro datos" (PDF, hoja 1)
const DATOS4 = [
  { b: "41 voces", t: "con acento argentino, 28 de mujer y 13 de hombre" },
  { b: "0800 · 0810", t: "y numeración regional, entrantes y salientes" },
  { b: "4 en 1", t: "número, agente, voces y WhatsApp" },
  { b: "1 API", t: "llamadas, campañas, contactos y resultados" },
];

/** 0. Intro oscura: la portada del PDF. */
export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.45, 0.7);
  const remate = useIn(en("a1", "de cada") - 0.1, 0.6);
  const sub = useIn(1.3, 0.6);
  const idx = [usePop(1.9), usePop(2.1), usePop(2.3), usePop(2.5)];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 110, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 320 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 236, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PROPUESTA DE ALIANZA · ZENNON BI · OCTUBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 316, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 82,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        La línea de voz argentina<br />
        <span style={{ color: C.accentOnDark, opacity: 0.25 + 0.75 * remate }}>de cada proyecto Dynamics 365.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 530, textAlign: "center", fontFamily: F.body, fontSize: 34, color: C.ctaMuted, opacity: sub }}>
        Voz con IA para sus proyectos de Dynamics 365 y Power Platform
      </div>
      <div style={{ position: "absolute", left: 160, right: 160, top: 680, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 22 }}>
        {DATOS4.map((s, i) => (
          <div key={s.b} style={{
            borderRadius: 20, padding: "24px 26px", background: "#16213a", border: "2px solid #23304d", height: 220, boxSizing: "border-box",
            transform: `scale(${idx[i]})`, opacity: Math.min(1, idx[i] * 1.5),
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 48, color: C.accentOnDark, whiteSpace: "nowrap", lineHeight: 1.05 }}>{s.b}</div>
            <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.ctaInk, marginTop: 12, lineHeight: 1.3 }}>{s.t}</div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

type Dato = { cifra: string; texto: string; frag: string; extra?: number };
// "Lo que ya hacen bien" (PDF, hoja 1); cada tarjeta entra con su parte de a2
const DATOS: Dato[] = [
  { cifra: "2018", texto: "implementando Dynamics 365, Power Platform y Power BI, como socios de Microsoft", frag: "dos mil" },
  { cifra: "32", texto: "clientes que muestran: aseguradoras, energía, bancos, universidades y cooperativas", frag: "treinta y dos" },
  { cifra: "+11.000", texto: "productores y organizadores de Federación Patronal en Dynamics 365 Sales", frag: "que lo muestran" },
  { cifra: "12", texto: "unidades de negocio de Federación Patronal, en todo el país, sobre FEDPAS 360", frag: "que lo muestran", extra: 0.25 },
];

/** 1. Lo que ya hacen bien: las cuatro cifras de la hoja 1 y la cita de Cristian. */
export const Bien: React.FC = () => {
  const ins = DATOS.map((d) => useIn(en("a2", d.frag) - 0.15 + (d.extra ?? 0), 0.6));
  const cita = useIn(AT.a3 - 0.6, 0.6);
  const voz = useIn(AT.a3 + 0.1, 0.6);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que ya hacen bien" text="Desde 2018 con Dynamics 365," accent="y clientes que lo muestran." size={60} />
      <div style={{ position: "absolute", left: 120, right: 120, top: 250, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24 }}>
        {DATOS.map((d, i) => (
          <div key={d.cifra} style={{
            height: 300, boxSizing: "border-box", padding: "28px 30px", background: "#fff", border: `2px solid ${C.line}`,
            borderTop: `10px solid ${C.ok}`, borderRadius: 24, boxShadow: shadowCard, opacity: ins[i], transform: `translateY(${(1 - ins[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 70, lineHeight: 1.05, color: C.ink, letterSpacing: "-0.015em" }}>{d.cifra}</div>
            <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.35, color: C.ink2, marginTop: 14 }}>{d.texto}</div>
          </div>
        ))}
      </div>

      <div style={{
        position: "absolute", left: 120, right: 120, top: 610, borderLeft: `8px solid ${C.accent}`, paddingLeft: 34, opacity: cita,
        transform: `translateY(${(1 - cita) * 20}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 42, lineHeight: 1.2, color: C.ink }}>
          “El 70% de esta plataforma está personalizada con el conocimiento y experiencia que el área comercial tenía.”
        </div>
        <div style={{ fontFamily: F.body, fontSize: 24, color: C.muted, marginTop: 12 }}>Cristian Ventura, sobre FEDPAS 360 de Federación Patronal</div>
      </div>
      <div style={{
        position: "absolute", left: 120, right: 120, top: 860, height: 104, boxSizing: "border-box", padding: "0 34px", borderRadius: 22,
        display: "flex", alignItems: "center", background: C.accentSoft, border: `2px solid #c9d7ff`, opacity: voz,
        fontFamily: F.body, fontSize: 28, color: C.accent2, lineHeight: 1.3,
      }}>
        <span><b>Con la voz, lo mismo:</b> el agente se arma con el conocimiento de cada cliente, y la integración es el oficio de Zennon.</span>
      </div>
      <Pie hoja="1 / 5" fuente="zennonbi.com (clientes y caso Federación Patronal), LinkedIn y CESSI, leídos el 22-oct-2026." />
    </AbsoluteFill>
  );
};

type Linea = { k: string; titulo: string; texto: string; oportunidad: string; at: number; main?: boolean };
// "Dónde encaja Atentina" (PDF, hoja 2): las dos destacadas y dos más, cada una con su línea de lucas (b1 a b4)
const LINEAS: Linea[] = [
  {
    k: "DYNAMICS 365 SALES · CRM KICKSTART", titulo: "El agente llama al lead apenas entra", at: AT.b1, main: true,
    texto: "El Sales Qualification Agent investiga y prepara un correo; el siguiente paso es la llamada.",
    oportunidad: "confirma el interés, califica y agenda la reunión del vendedor.",
  },
  {
    k: "DYNAMICS 365 CUSTOMER SERVICE", titulo: "El número del cliente atiende a toda hora", at: AT.b2, main: true,
    texto: "Para los clientes con volumen de llamadas: pagos, cooperativas, microcréditos y tercerizadas.",
    oportunidad: "toma el reclamo, identifica al cliente y deja el caso en Dataverse.",
  },
  {
    k: "DYNAMICS 365 FIELD SERVICE", titulo: "Visitas confirmadas el día anterior", at: AT.b3,
    texto: "Cada visita fallida es un técnico en la calle sin trabajo: una métrica que el cliente entiende.",
    oportunidad: "confirma, reprograma o avisa la demora en la orden.",
  },
  {
    k: "CUSTOMER INSIGHTS · JOURNEYS", titulo: "Llamada o WhatsApp, un paso del recorrido", at: AT.b4,
    texto: "Recordatorios, vencimientos y cobranza temprana, dentro del recorrido que ya diseñan.",
    oportunidad: "el segmento dispara la campaña; el resultado vuelve al contacto.",
  },
];
const TAMBIEN = ["Contact Center", "Power Pages", "Copilot Studio", "Power BI", "Para partners"];

/** 2. Dónde encaja Atentina: cuatro tarjetas, una por línea de la locución de lucas, y el resto en chips. */
export const Lineas: React.FC = () => {
  const p = LINEAS.map((x) => useIn(x.at - 0.1, 0.6));
  const op = LINEAS.map((x) => useIn(x.at + 1.4, 0.6));
  const tira = useIn(AT.b4 + 2.2, 0.6);
  const chips = TAMBIEN.map((_, i) => usePop(AT.b4 + 2.4 + i * 0.12));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Dónde encaja Atentina" text="Voz en cada línea que venden," accent="sin montar telefonía." size={58} />
      {LINEAS.map((x, i) => {
        const left = i % 2 === 0 ? 120 : 975;
        const top = i < 2 ? 246 : 566;
        return (
          <div key={x.k} style={{
            position: "absolute", left, top, width: 825, height: 296, boxSizing: "border-box", padding: "22px 34px",
            background: x.main ? `linear-gradient(180deg, ${C.accentSoft}, #fff 80%)` : "#fff",
            border: x.main ? `3px solid ${C.accent}` : `2px solid ${C.line}`, borderLeft: `10px solid ${C.accent}`, borderRadius: 24, boxShadow: shadowCard,
            opacity: p[i], transform: `translateY(${(1 - p[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: x.main ? C.accent : C.muted }}>{x.k}</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 35, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.01em", marginTop: 6 }}>{x.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 23, lineHeight: 1.35, color: C.ink2, marginTop: 10 }}>{x.texto}</div>
            <div style={{
              position: "absolute", left: 34, right: 34, bottom: 20, borderTop: `2px solid ${C.line}`, paddingTop: 10,
              fontFamily: F.body, fontSize: 23, lineHeight: 1.3, color: C.accent2, opacity: op[i],
            }}>
              <b>Oportunidad:</b> {x.oportunidad}
            </div>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 120, right: 120, top: 892, display: "flex", alignItems: "center", gap: 16, opacity: tira }}>
        <span style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted, marginRight: 8 }}>Y TAMBIÉN</span>
        {TAMBIEN.map((d, i) => (
          <div key={d} style={{
            fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.ink, background: "#fff", border: `2px solid ${C.line2}`,
            borderRadius: 999, padding: "8px 22px", transform: `scale(${chips[i]})`, whiteSpace: "nowrap",
          }}>{d}</div>
        ))}
      </div>
      <Pie hoja="2 / 5" fuente="zennonbi.com (soluciones, clientes y CRM KickStart), leído el 22-oct-2026." />
    </AbsoluteFill>
  );
};

// "Cómo se pone en marcha" (PDF, hoja 5)
const OFERTA = [
  { k: "DESDE HOY", b: "Acceso para probar", frag: "Primero",
    t: "Registro en atentina.com.ar: panel, API keys, agentes, las 41 voces y llamadas desde el navegador." },
  { k: "EN LA REUNIÓN", b: "Demo técnica, 30 min", frag: "una demo",
    t: "Con un Dynamics de prueba de Zennon: se carga un lead con el celular de Cristian, suena y la actividad aparece en el lead." },
  { k: "PARA DECIDIR", b: "Piloto de 30 días", frag: "un piloto",
    t: "Un caso real, en Zennon o en un cliente de su cartera, con número argentino y soporte directo." },
];
const DESPUES = ["Primer cliente", "Conector y tablero", "Copilot Studio", "Acuerdo de aliado"];

/** 5. Puesta en marcha: acceso, demo técnica (destacada) y piloto de 30 días; después del piloto. */
export const Marcha: React.FC = () => {
  const ins = OFERTA.map((o) => useIn(en("a8", o.frag) - 0.15, 0.6));
  const tira = useIn(en("a8", "con un caso"), 0.6);
  const chips = DESPUES.map((_, i) => usePop(en("a8", "con un caso") + 0.3 + i * 0.15));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Cómo se pone en marcha" text="Primero la demo técnica." accent="Después, 30 días de piloto." size={60} />
      <div style={{ position: "absolute", left: 120, right: 120, top: 270, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 30 }}>
        {OFERTA.map((o, i) => (
          <div key={o.k} style={{
            height: 390, boxSizing: "border-box", padding: "32px 34px", borderRadius: 26, boxShadow: shadowCard,
            background: i === 1 ? `linear-gradient(180deg, ${C.accentSoft}, #fff 85%)` : "#fff",
            border: i === 1 ? `3px solid ${C.accent}` : `2px solid ${C.line}`,
            opacity: ins[i], transform: `translateY(${(1 - ins[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: i === 1 ? C.accent : C.muted }}>{o.k}</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, lineHeight: 1.1, color: C.accent, marginTop: 14 }}>{o.b}</div>
            <div style={{ fontFamily: F.body, fontSize: 28, lineHeight: 1.4, color: C.ink2, marginTop: 18 }}>{o.t}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 760, opacity: tira }}>
        <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted }}>DESPUÉS DEL PILOTO</div>
        <div style={{ display: "flex", gap: 18, marginTop: 18 }}>
          {DESPUES.map((d, i) => (
            <div key={d} style={{
              fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, background: "#fff", border: `2px solid ${C.line2}`,
              borderRadius: 999, padding: "14px 30px", transform: `scale(${chips[i]})`,
            }}>{d}</div>
          ))}
        </div>
      </div>
      <Pie hoja="5 / 5" fuente="Probar el acceso no tiene costo." />
    </AbsoluteFill>
  );
};

/** 6. Cierre: solo la pregunta, con el contacto de Atentina chico abajo. */
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
        <div style={{ fontFamily: F.mono, fontSize: 24, color: C.ctaMuted }}>atentina.com.ar · 0800-220-1233 · hola@atentina.com.ar</div>
      </div>
    </AbsoluteFill>
  );
};

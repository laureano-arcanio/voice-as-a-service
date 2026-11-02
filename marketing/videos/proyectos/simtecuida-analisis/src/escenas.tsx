import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

export const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

/** Pie de página como el del PDF. */
export const Pie: React.FC<{ fuente?: string }> = ({ fuente }) => {
  const o = useIn(0.5, 0.5);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · SIM TE CUIDA</span>
    </div>
  );
};

// Lo que vimos: las cuatro cifras del PDF v2, página 1 (sitio de SIM, leído el 2-nov-2026). Momentos de a1:
// "a toda hora," ~1,2 · "en CABA y GBA," 2,35 · "y asignación en dos a cuatro horas." 3,8
const VIMOS = [
  { cifra: "24 h", texto: "Los 365 días: guardias de día y de noche, y coordinación a toda hora.", at: 1.2 },
  { cifra: "CABA y GBA", texto: "Con zonas norte, oeste y sur, hasta La Plata.", at: 2.35 },
  { cifra: "26", texto: "Sanatorios, clínicas y hospitales nombrados en sus páginas de zona.", at: 3.05 },
  { cifra: "2 a 4 h", texto: "La asignación que prometen para internación o domicilio.", at: 3.8 },
];

/** 1. Intro en blanco: logo oscuro y lo que vimos de la empresa. */
export const Intro: React.FC = () => {
  const logo = usePop(0.05);
  const titulo = useIn(0.2, 0.6);
  const ins = VIMOS.map((d) => useIn(AT.a1 + d.at, 0.5));
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 72, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 280 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 182, textAlign: "center", fontFamily: F.mono, fontSize: 25, letterSpacing: "0.1em", color: C.accent, opacity: titulo }}>
        PROPUESTA · SIM TE CUIDA · NOVIEMBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 240, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 84,
        lineHeight: 1.08, color: C.ink, letterSpacing: "-0.015em", opacity: titulo, transform: `translateY(${(1 - titulo) * 20}px)`,
      }}>
        En SIM Te Cuida, <span style={{ color: C.accent }}>esto es lo que vimos.</span>
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 440, display: "flex", gap: 22 }}>
        {VIMOS.map((d, i) => (
          <div key={d.cifra} style={{
            flex: 1, height: 400, boxSizing: "border-box", padding: "40px 32px", background: "#fff", border: `2px solid ${C.line}`, borderTop: `10px solid ${C.ok}`,
            borderRadius: 24, boxShadow: shadowCard, opacity: ins[i], transform: `translateY(${(1 - ins[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 56, lineHeight: 1.08, color: C.ink, letterSpacing: "-0.02em", whiteSpace: "nowrap" }}>{d.cifra}</div>
            <div style={{ fontFamily: F.body, fontSize: 32, lineHeight: 1.32, color: C.ink2, marginTop: 24 }}>{d.texto}</div>
          </div>
        ))}
      </div>
      <Pie fuente="Fuente: simtecuida.com.ar, leído el 2-nov-2026. El conteo de 26 es nuestro, sobre esas páginas." />
    </AbsoluteFill>
  );
};

// Las oportunidades: hoja "Dónde podríamos mejorar con Atentina" del PDF v1, en tres tarjetas. Momentos de a2:
// "Todo entra por un mismo canal." 0,1 · "Reconocer al cliente," 2,0 · "y separar lo urgente," 3,35
const OPS = [
  { rotulo: "Canales", titulo: "Todo entra por un mismo canal", op: "Que cada consulta se ordene por motivo antes de llegar a una persona.", at: 0.1 },
  { rotulo: "Clientes", titulo: "Reconocer a quien ya es cliente", op: "Que la persona que atiende sepa quién es antes de hablar.", at: 2.0 },
  { rotulo: "Prioridad", titulo: "Separar lo urgente", op: "Dar prioridad, con el criterio de ustedes, a lo que puede ser una emergencia.", at: 3.35 },
];

/** 2. Dónde están las oportunidades: lecturas nuestras, sin fallas ni quejas. */
export const Oportunidades: React.FC = () => {
  const ins = OPS.map((o) => useIn(AT.a2 + o.at, 0.5));
  const promesa = useIn(AT.a2 + 4.55, 0.5);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Dónde podríamos mejorar con Atentina" text="La oportunidad está en" accent="el primer contacto." />
      <div style={{ position: "absolute", left: 120, right: 120, top: 260, display: "flex", gap: 24 }}>
        {OPS.map((o, i) => (
          <div key={o.rotulo} style={{
            flex: 1, height: 480, boxSizing: "border-box", padding: "36px 38px", background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.accent}`,
            borderRadius: 24, boxShadow: shadowCard, opacity: ins[i], transform: `translateY(${(1 - ins[i]) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.mono, fontSize: 22, letterSpacing: "0.08em", textTransform: "uppercase", color: C.accent }}>{o.rotulo}</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 48, lineHeight: 1.1, color: C.ink, marginTop: 18, letterSpacing: "-0.01em" }}>{o.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 30, lineHeight: 1.32, color: C.ink2, marginTop: 26 }}>
              <b style={{ color: C.accent }}>Oportunidad:</b> {o.op}
            </div>
          </div>
        ))}
      </div>
      <div style={{
        position: "absolute", left: 120, right: 120, top: 776, height: 150, boxSizing: "border-box", display: "flex", alignItems: "center", justifyContent: "center", gap: 20,
        background: C.accentSoft, border: `2px solid ${C.accent}`, borderRadius: 22, opacity: promesa, transform: `translateY(${(1 - promesa) * 20}px)`,
        fontFamily: F.display, fontWeight: 800, fontSize: 44, color: C.ink, letterSpacing: "-0.01em",
      }}>
        <Icon name="clock" size={50} color={C.accent} />
        Más fácil cumplir lo que prometen: <span style={{ color: C.accent }}>asignar en 2 a 4 horas.</span>
      </div>
      <Pie fuente="Lecturas nuestras de lo que publican y de lo que nos pidieron; las confirmamos con ustedes en la reunión." />
    </AbsoluteFill>
  );
};

// Presupuesto: mismo texto y misma aclaración de capacidad que el PDF v2, página 5. Momentos de a7:
// "Plan Mostrador," 0,1 · "más mantenimiento del CRM:" 1,1 · "treinta y nueve mil pesos por mes." 2,75
const FILAS = [
  { t: "Plan Mostrador", sub: "", precio: "$ 29.000", at: 0.1 },
  { t: "Mantenimiento del sistema CRM", sub: "Para el almacenaje de los pacientes y las consultas. Incluye el teléfono 0800, si lo quieren.", precio: "$ 10.000", at: 1.1 },
];
const INCLUYE = ["La puesta en marcha", "El número de teléfono", "El WhatsApp", "La carga inicial de clientes"];

/** 7. Presupuesto. */
export const Presupuesto: React.FC = () => {
  const t = useT();
  const v = (s: number) => AT.a7 + s;
  const tabla = useIn(v(0), 0.5);
  const on = FILAS.map((x) => interpolate(t, [v(x.at), v(x.at + 0.3)], [0, 1], CLAMP));
  const total = useIn(v(2.75), 0.5);
  const inc = useIn(v(0.6), 0.5);
  const nota = useIn(v(1.2), 0.5);
  return (
    <AbsoluteFill>
      <Headline eyebrow="La propuesta" text="Presupuesto:" accent="$ 39.000 por mes." />
      <div style={{
        position: "absolute", left: 120, right: 120, top: 220, borderRadius: 24, overflow: "hidden", border: `2px solid ${C.line2}`, background: "#fff",
        boxShadow: shadowCard, opacity: tabla, transform: `translateY(${(1 - tabla) * 30}px)`,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", padding: "14px 36px", background: C.bg2, borderBottom: `2px solid ${C.line}`, fontFamily: F.mono, fontSize: 21, letterSpacing: "0.05em", color: C.muted }}>
          <span>CONCEPTO</span><span>POR MES, A NOVIEMBRE DE 2026</span>
        </div>
        {FILAS.map((x, i) => (
          <div key={x.t} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 40, padding: "0 36px", height: 112, borderBottom: `2px solid ${C.line}`, opacity: 0.35 + 0.65 * on[i] }}>
            <div>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ink }}>{x.t}</div>
              {x.sub ? <div style={{ fontFamily: F.body, fontSize: 25, color: C.ink2, marginTop: 4 }}>{x.sub}</div> : null}
            </div>
            <div style={{ fontFamily: F.mono, fontSize: 40, color: C.ink, whiteSpace: "nowrap" }}>{x.precio}</div>
          </div>
        ))}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 36px", height: 112, background: interpolate(total, [0, 1], [0, 1]) > 0.5 ? C.accentSoft : "#fff" }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, color: C.ink }}>Total</div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, color: C.accent, opacity: total, transform: `scale(${0.9 + 0.1 * total})`, transformOrigin: "right center", whiteSpace: "nowrap" }}>$ 39.000 por mes</div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 636, opacity: inc }}>
        <div style={{ fontFamily: F.mono, fontSize: 21, letterSpacing: "0.06em", color: C.accent }}>LA PROPUESTA INCLUYE</div>
        <div style={{ display: "flex", gap: 16, marginTop: 14 }}>
          {INCLUYE.map((x) => (
            <div key={x} style={{ flex: 1, height: 84, boxSizing: "border-box", display: "flex", alignItems: "center", gap: 12, padding: "0 20px", background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, fontFamily: F.body, fontWeight: 700, fontSize: 27, color: C.ink, whiteSpace: "nowrap" }}>
              <Icon name="check" size={32} color={C.ok} />{x}
            </div>
          ))}
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 800, boxSizing: "border-box", padding: "22px 34px", background: C.bg2, border: `2px solid ${C.line}`, borderRadius: 20, fontFamily: F.body, fontSize: 30, lineHeight: 1.32, color: C.ink2, opacity: nota }}>
        La capacidad (llamadas simultáneas, minutos y personas en rotación) se define con ustedes en el relevamiento, según su guardia.
        Los minutos que entran por un 0800 descuentan el doble del plan.
      </div>
      <Pie />
    </AbsoluteFill>
  );
};

/** 8. Cierre en blanco: solo la pregunta, con el contacto de Atentina chico abajo. */
export const Cierre: React.FC = () => {
  const line = useIn(0.2, 0.6);
  const contacto = useIn(0.9, 0.5);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 96, lineHeight: 1.1, color: C.ink, opacity: line, transform: `translateY(${(1 - line) * 24}px)`, letterSpacing: "-0.02em",
      }}>
        ¿Agendamos una reunión<br /><span style={{ color: C.accent }}>personalmente?</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 930, display: "flex", justifyContent: "center", alignItems: "center", gap: 28, opacity: contacto }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 150 }} />
        <div style={{ fontFamily: F.mono, fontSize: 24, color: C.muted }}>atentina.com.ar · 0800-220-1233 · hola@atentina.com.ar</div>
      </div>
    </AbsoluteFill>
  );
};


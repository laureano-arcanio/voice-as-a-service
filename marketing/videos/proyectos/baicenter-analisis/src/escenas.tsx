import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

/** Pie de página como el del PDF: "Atentina · BAIC Center / Grupo Signature" y la sección. */
export const Pie: React.FC<{ fuente?: string; seccion: string }> = ({ fuente, seccion }) => {
  const o = useIn(0.6, 0.6);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · BAIC CENTER / GRUPO SIGNATURE · {seccion}</span>
    </div>
  );
};

const SECCIONES = ["Lo que ya hacen bien", "Dónde podríamos mejorar con Atentina", "Lo que piden sus clientes", "La propuesta"];

/** 0. Intro oscura: la portada del PDF. */
export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.45, 0.7);
  const sub = useIn(1.6, 0.6);
  const idx = [usePop(2.3), usePop(2.5), usePop(2.7), usePop(2.9)];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 130, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 340 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 262, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PROPUESTA · BAIC CENTER / GRUPO SIGNATURE · OCTUBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 340, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 86,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        El cliente primero,<br /><span style={{ color: C.accentOnDark }}>también en el primer minuto.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 568, textAlign: "center", fontFamily: F.body, fontSize: 34, color: C.ctaMuted, opacity: sub }}>
        Un asesor de guardia 24/7 en sus WhatsApp y su línea
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 720, display: "flex", justifyContent: "center", gap: 18 }}>
        {SECCIONES.map((s, i) => (
          <div key={s} style={{
            display: "flex", alignItems: "center", gap: 14, borderRadius: 18, padding: "16px 24px", background: "#16213a",
            border: "2px solid #23304d", transform: `scale(${idx[i]})`, opacity: Math.min(1, idx[i] * 1.5),
          }}>
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.accentOnDark }}>{i + 1}</span>
            <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 27, color: C.ctaInk, whiteSpace: "nowrap" }}>{s}</span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

type Dato = { cifra: string; texto: string; fuente: string; at: number };
// Momentos de a2 (s desde que arranca la voz): "Nueve años," 2,95 · "cuatro marcas," 3,7 · "y flotas como la de EPEC." 4,7
const DATOS: Dato[] = [
  { cifra: "9 años", texto: "De BAIC Center en Córdoba, dentro de un grupo que nació en 2017.", fuente: "Prensa de Córdoba (2026) y LinkedIn", at: 2.95 },
  { cifra: "4 marcas", texto: "BAIC, Arcfox, Mitsubishi y Foton, con ventas, posventa, repuestos y usados.", fuente: "Sus cuatro sitios", at: 3.7 },
  { cifra: "3.300 m²", texto: "Entre el showroom de Av. Colón (800 m²) y la Sucursal Norte de Foton (2.500 m²).", fuente: "Sus sitios", at: 4.25 },
  { cifra: "7 años", texto: "De garantía BAIC, o 100.000 km, y flotas como la de EPEC.", fuente: "Sus sitios y LinkedIn", at: 4.7 },
];

/** 1. Lo que ya hacen bien: cuatro datos en tarjetas verdes. */
export const Bien: React.FC = () => {
  const ins = DATOS.map((d) => useIn(AT.a2 + d.at, 0.6));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que ya hacen bien" text="En BAIC Center ya hicieron" accent="lo difícil." />
      {DATOS.map((d, i) => {
        const x = i % 2 === 0 ? 120 : 975;
        const y = i < 2 ? 268 : 620;
        const p = ins[i];
        return (
          <div key={d.cifra} style={{
            position: "absolute", left: x, top: y, width: 825, height: 320, boxSizing: "border-box", padding: "34px 40px",
            background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.ok}`, borderRadius: 24, boxShadow: shadowCard,
            opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 76, lineHeight: 1.05, color: C.ink, letterSpacing: "-0.015em" }}>{d.cifra}</div>
            <div style={{ fontFamily: F.body, fontSize: 30, lineHeight: 1.35, color: C.ink2, marginTop: 16 }}>{d.texto}</div>
            <div style={{ position: "absolute", left: 40, bottom: 26, fontFamily: F.mono, fontSize: 18, color: C.muted }}>{d.fuente}</div>
          </div>
        );
      })}
      <Pie seccion="1 / 4" />
    </AbsoluteFill>
  );
};

const CITA = ["El", "cliente", "primero."];
// Lo que muestra el lema (PDF, página 1)
const PRUEBAS = [
  "Edgardo contesta en persona las reseñas de Google.",
  "Trajo el primer Prius y el primer eléctrico homologado.",
  "Ya atienden por WhatsApp desde sus cuatro sitios.",
];

/** 1b. El lema: "El cliente primero.", y lo que lo demuestra. */
export const Cita: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a3;
  // a3: "Y lo resume el lema de la casa:" 0–1,8 · "el cliente primero." 1,95–3,1
  const barra = useIn(0.15, 0.6);
  const firma = useIn(AT.a3 + 0.9, 0.6);
  const pruebas = PRUEBAS.map((_, i) => useIn(AT.a3 + 1.3 + i * 0.3, 0.5));
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 120, top: 76 }}>
        <div style={{ fontFamily: F.mono, fontSize: 24, letterSpacing: "0.08em", color: C.accent }}>LO QUE YA HACEN BIEN</div>
      </div>
      <div style={{ position: "absolute", left: 200, top: 250, width: 12, height: 300 * barra, borderRadius: 6, background: C.accent }} />
      <div style={{ position: "absolute", left: 260, right: 160, top: 250, fontFamily: F.display, fontWeight: 800, fontSize: 150, lineHeight: 1.05, color: C.ink, letterSpacing: "-0.025em" }}>
        <span style={{ color: C.line2 }}>“</span>
        {CITA.map((w, i) => {
          const p = interpolate(t, [1.9 + i * 0.35, 2.25 + i * 0.35], [0, 1], { ...CLAMP, easing: EASE });
          const ult = i === CITA.length - 1;
          return <span key={i} style={{ opacity: 0.12 + 0.88 * p, color: ult ? C.accent : C.ink }}>{w}{ult ? "" : " "}</span>;
        })}
        <span style={{ color: C.line2 }}>”</span>
      </div>
      <div style={{ position: "absolute", left: 260, top: 470, fontFamily: F.body, fontSize: 34, color: C.ink2, opacity: firma }}>
        El lema de la casa. <b style={{ color: C.ink }}>Y se ve:</b>
      </div>
      {PRUEBAS.map((x, i) => (
        <div key={x} style={{
          position: "absolute", left: 260, top: 590 + i * 92, display: "flex", alignItems: "center", gap: 18, fontFamily: F.body, fontSize: 36,
          color: C.ink, opacity: pruebas[i], transform: `translateX(${(1 - pruebas[i]) * -24}px)`,
        }}>
          <Icon name="check" size={38} color={C.ok} />{x}
        </div>
      ))}
      <Pie seccion="1 / 4" fuente="Google Maps, LinkedIn y prensa de Córdoba, leídos el 20-oct-2026." />
    </AbsoluteFill>
  );
};

/** 6. Cierre: solo la pregunta, con el contacto de Atentina chico abajo. */
export const Cierre: React.FC = () => {
  const line = useIn(0.35, 0.7);
  const contacto = useIn(1.4, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 96, lineHeight: 1.1, color: C.ctaInk, opacity: line, transform: `translateY(${(1 - line) * 24}px)`, letterSpacing: "-0.02em",
      }}>
        ¿Agendamos una reunión<br /><span style={{ color: C.accentOnDark }}>personalmente?</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 930, display: "flex", justifyContent: "center", alignItems: "center", gap: 28, opacity: contacto }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 150 }} />
        <div style={{ fontFamily: F.mono, fontSize: 24, color: C.ctaMuted }}>atentina.com.ar · 0800-220-1233</div>
      </div>
    </AbsoluteFill>
  );
};

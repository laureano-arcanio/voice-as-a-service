import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Icon, Headline, useIn, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

/** Pie de página como el del PDF: "Atentina · SQL Amoblamientos" y la sección. */
export const Pie: React.FC<{ fuente?: string; seccion: string }> = ({ fuente, seccion }) => {
  const o = useIn(0.6, 0.6);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · SQL AMOBLAMIENTOS · {seccion}</span>
    </div>
  );
};

const SECCIONES = ["Lo que ya hacen bien", "Dónde podríamos mejorar con Atentina", "Lo que valoran sus clientes", "La propuesta"];

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
        PROPUESTA · SQL AMOBLAMIENTOS · OCTUBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 340, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 86,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Cada consulta con respuesta,<br /><span style={{ color: C.accentOnDark }}>cada cliente al tanto de lo suyo.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 568, textAlign: "center", fontFamily: F.body, fontSize: 34, color: C.ctaMuted, opacity: sub }}>
        Un asesor de guardia 24/7 en su WhatsApp y su línea
      </div>
      <div style={{ position: "absolute", left: 100, right: 100, top: 720, display: "flex", justifyContent: "center", gap: 18 }}>
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
// Momentos de a2 (s desde que arranca la voz): "Amoblamientos" 1,0 · "lo difícil:" 2,4 · "veinte locales," 3,9 ·
// "en nueve provincias." 5,25
const DATOS: Dato[] = [
  { cifra: "Desde 1981", texto: "Diseñando, fabricando e instalando muebles 100 % a medida en Córdoba.", fuente: "D&F Muebles (2015)", at: 1.0 },
  { cifra: "4.000 m²", texto: "De planta propia en San Roque, con 10 máquinas computarizadas y 70 personas.", fuente: "InfoNegocios (abril de 2025)", at: 2.4 },
  { cifra: "20 locales", texto: "De venta en 9 provincias, propios y franquicias, y un showroom nuevo de 400 m².", fuente: "Su sitio e InfoNegocios (2025)", at: 3.9 },
  { cifra: "183 reseñas", texto: "En Google de la casa central, con 4,3 de promedio y asesores elogiados por su nombre.", fuente: "Google Maps, 22-oct-2026", at: 5.25 },
];

/** 1. Lo que ya hacen bien: cuatro datos en tarjetas verdes. */
export const Bien: React.FC = () => {
  const ins = DATOS.map((d) => useIn(AT.a2 + d.at, 0.6));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que ya hacen bien" text="En SQL Amoblamientos ya hicieron" accent="lo difícil." />
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

// Cita textual (Punto a Punto, 17-nov-2021), recortada a la primera parte
const CITA = ["Cumplimos", "a", "rajatabla", "con", "los", "tiempos", "estipulados."];
// Cuándo dice cada palabra (s desde que arranca a3), por las pausas de la toma
const PALABRA = [2.12, 2.65, 2.85, 3.76, 3.88, 4.0, 4.29];
const ACENTO = 5; // desde "tiempos"

/** 1b. La cita de Jorge Urizar, palabra por palabra con la voz. */
export const Cita: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a3;
  // a3: "En palabras de Jorge Urizar:" 0–1,76 · "Cumplimos a rajatabla" 2,12 · "con los tiempos" 3,76 · "estipulados." 4,29–4,96
  const barra = useIn(0.15, 0.6);
  const firma = useIn(AT.a3 + 0.4, 0.6);
  const promesa = useIn(AT.a3 + 3.9, 0.6);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 120, top: 76 }}>
        <div style={{ fontFamily: F.mono, fontSize: 24, letterSpacing: "0.08em", color: C.accent }}>LO QUE YA HACEN BIEN</div>
      </div>
      <div style={{ position: "absolute", left: 200, top: 250, width: 12, height: 250 * barra, borderRadius: 6, background: C.accent }} />
      <div style={{ position: "absolute", left: 260, right: 140, top: 240, fontFamily: F.display, fontWeight: 800, fontSize: 104, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.025em" }}>
        <span style={{ color: C.line2 }}>“</span>
        {CITA.map((w, i) => {
          const p = interpolate(t, [PALABRA[i] - 0.05, PALABRA[i] + 0.3], [0, 1], { ...CLAMP, easing: EASE });
          const acc = i >= ACENTO;
          return <span key={i} style={{ opacity: 0.12 + 0.88 * p, color: acc ? C.accent : C.ink }}>{w}{i === CITA.length - 1 ? "" : " "}</span>;
        })}
        <span style={{ color: C.line2 }}>”</span>
      </div>
      <div style={{ position: "absolute", left: 260, top: 540, fontFamily: F.body, fontSize: 34, color: C.ink2, opacity: firma }}>
        <b style={{ color: C.ink }}>Jorge Urizar,</b> fundador, en Punto a Punto (noviembre de 2021)
      </div>
      <div style={{
        position: "absolute", left: 260, right: 140, top: 680, display: "flex", alignItems: "center", gap: 18, padding: "26px 32px",
        borderRadius: 22, background: C.accentSoft, border: "2px solid #c9d7ff", opacity: promesa, transform: `translateY(${(1 - promesa) * 20}px)`,
      }}>
        <Icon name="check" size={40} color={C.accent} />
        <span style={{ fontFamily: F.body, fontSize: 34, color: C.ink }}>
          Esta propuesta quiere ayudar a que el cliente <b style={{ color: C.accent2 }}>vea esa promesa día a día.</b>
        </span>
      </div>
      <Pie seccion="1 / 4" fuente="Punto a Punto (17-nov-2021), cita textual." />
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

import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

// Colores del PDF experto-propuesta v1: verde para lo que hacen bien, naranja para el "Hoy", azul para "Con Atentina"
export const NAR = "#c2410c";
export const NAR_SOFT = "#fff4ed";

/** Pie de página como el del PDF: "Atentina · Experto Construcción Inteligente" y la sección. */
export const Pie: React.FC<{ fuente?: string; seccion: string }> = ({ fuente, seccion }) => {
  const o = useIn(0.6, 0.6);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · EXPERTO CONSTRUCCIÓN INTELIGENTE · {seccion}</span>
    </div>
  );
};

const SECCIONES = ["Lo que ya hacen bien", "Dónde podríamos mejorar", "La solución propuesta", "El panel"];

/** 0. Intro en blanco (VIDEOS.md): la portada del PDF, con logo oscuro. */
export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.45, 0.7);
  const sub = useIn(1.4, 0.6);
  const idx = [usePop(2.2), usePop(2.4), usePop(2.6), usePop(2.8)];
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 320 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 246, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accent, opacity: useIn(0.3, 0.5) }}>
        PROPUESTA · EXPERTO CONSTRUCCIÓN INTELIGENTE · NOVIEMBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 322, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 78,
        lineHeight: 1.1, color: C.ink, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Atención 24 horas por WhatsApp, teléfono y web,<br /><span style={{ color: C.accent }}>con todo a la vista.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 545, textAlign: "center", fontFamily: F.body, fontSize: 36, color: C.ink2, opacity: sub }}>
        Cada consulta atendida en el momento, y lista para el asesor de su sucursal.
      </div>
      <div style={{ position: "absolute", left: 100, right: 100, top: 700, display: "flex", justifyContent: "center", gap: 18 }}>
        {SECCIONES.map((s, i) => (
          <div key={s} style={{
            display: "flex", alignItems: "center", gap: 14, borderRadius: 18, padding: "16px 24px", background: "#fff",
            border: `2px solid ${C.line}`, boxShadow: shadowCard, transform: `scale(${idx[i]})`, opacity: Math.min(1, idx[i] * 1.5),
          }}>
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.accent }}>{i + 1}</span>
            <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 27, color: C.ink, whiteSpace: "nowrap" }}>{s}</span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

type Dato = { cifra: string; chica?: boolean; texto: string; fuente: string; at: number; estrellas?: boolean };
// Momentos de a2 (s desde que arranca la voz), por las pausas de la toma:
// "Veintidós años," 2,7 · "cuatro locales," 3,7 · "y un asesoramiento que sus clientes recomiendan." 4,65–7,0
const DATOS: Dato[] = [
  { cifra: "22 años", texto: "Desde la maderera de Santa María de Punilla, en 2004.", fuente: "Su sitio e Infonegocios (2023)", at: 2.7 },
  { cifra: "4 locales", texto: "Punilla, Carlos Paz, Zona Sur y un centro de distribución de 5.300 m².", fuente: "Su sitio", at: 3.7 },
  { cifra: "752 reseñas", texto: "En Google entre los cuatro locales, con 4,3 a 4,5 de promedio.", fuente: "Google Maps, 11-nov-2026", at: 4.65, estrellas: true },
  { cifra: "19 marcas · 331 productos", chica: true, texto: "En su catálogo; distribuidor Knauf.", fuente: "Su sitio", at: 5.7 },
];

const Estrellas: React.FC<{ p: number }> = ({ p }) => (
  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
    {[0, 1, 2, 3, 4].map((i) => {
      const lleno = Math.max(0, Math.min(1, p * 4.4 - i));
      return (
        <svg key={i} viewBox="0 0 24 24" width={34} height={34}>
          <defs>
            <linearGradient id={`st${i}`}>
              <stop offset={lleno} stopColor="#f5b301" />
              <stop offset={lleno} stopColor={C.line} />
            </linearGradient>
          </defs>
          <path d="M12 2.5l2.9 6 6.6.8-4.9 4.5 1.3 6.5L12 17l-5.9 3.3 1.3-6.5L2.5 9.3l6.6-.8z" fill={`url(#st${i})`} />
        </svg>
      );
    })}
    <span style={{ fontFamily: F.mono, fontSize: 26, color: C.ink, marginLeft: 8, opacity: p }}>4,3 a 4,5</span>
  </div>
);

/** 1. Lo que ya hacen bien: cuatro datos en tarjetas verdes. */
export const Bien: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ins = DATOS.map((d) => useIn(AT.a2 + d.at, 0.6));
  const est = interpolate(frame / fps, [AT.a2 + DATOS[2].at + 0.2, AT.a2 + DATOS[2].at + 1.2], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que ya hacen bien" text="En Experto ya hicieron" accent="lo difícil." />
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
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: d.chica ? 60 : 76, lineHeight: 1.05, color: C.ink, letterSpacing: "-0.015em", whiteSpace: "nowrap" }}>{d.cifra}</div>
            <div style={{ fontFamily: F.body, fontSize: 29, lineHeight: 1.35, color: C.ink2, marginTop: 16 }}>{d.texto}</div>
            {d.estrellas ? <div style={{ marginTop: 12 }}><Estrellas p={est} /></div> : null}
            <div style={{ position: "absolute", left: 40, bottom: 26, fontFamily: F.mono, fontSize: 18, color: C.muted }}>{d.fuente}</div>
          </div>
        );
      })}
      <Pie seccion="1 / 4" />
    </AbsoluteFill>
  );
};

// v2: la cita de los dueños (quintuplicar la capacidad productiva) no tenía sentido en el contexto (pedido del usuario);
// va una reseña de 5 estrellas de la ficha de Carlos Paz, sin nombre, la misma del PDF v2. En pantalla, sin el "!" del original.
const CITA = ["Gran", "asesoramiento", "para", "quienes", "justamente", "no", "somos", "expertos."];

/** 1b. Lo que dicen sus clientes: una reseña de 5 estrellas, palabra por palabra. */
export const Cita: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a3;
  // a3 (gonzalo): "Lo dicen sus clientes:" 0,1–1,1; la reseña, de 1,23 a 4,26 (~0,38 s por palabra)
  const barra = useIn(0.15, 0.6);
  const estrellas = useIn(AT.a3 + 0.6, 0.5);
  const firma = useIn(AT.a3 + 3.9, 0.6);
  const check = useIn(AT.a3 + 4.4, 0.6);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 120, top: 76 }}>
        <div style={{ fontFamily: F.mono, fontSize: 24, letterSpacing: "0.08em", color: C.accent }}>LO QUE DICEN SUS CLIENTES</div>
      </div>
      <div style={{ position: "absolute", left: 200, top: 250, width: 12, height: 400 * barra, borderRadius: 6, background: C.accent }} />
      <div style={{ position: "absolute", left: 260, top: 240, display: "flex", gap: 8, opacity: estrellas }}>
        {[0, 1, 2, 3, 4].map((i) => (
          <svg key={i} viewBox="0 0 24 24" width={44} height={44}>
            <path d="M12 2.5l2.9 6 6.6.8-4.9 4.5 1.3 6.5L12 17l-5.9 3.3 1.3-6.5L2.5 9.3l6.6-.8z" fill="#f5b301" />
          </svg>
        ))}
      </div>
      <div style={{ position: "absolute", left: 260, right: 160, top: 320, fontFamily: F.display, fontWeight: 800, fontSize: 100, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.02em" }}>
        <span style={{ color: C.line2 }}>“</span>
        {CITA.map((w, i) => {
          const p = interpolate(t, [1.2 + i * 0.38, 1.55 + i * 0.38], [0, 1], { ...CLAMP, easing: EASE });
          const acento = i <= 1;
          return (
            <span key={i} style={{ opacity: 0.12 + 0.88 * p, color: acento ? C.accent : C.ink }}>{w}{i === CITA.length - 1 ? "" : " "}</span>
          );
        })}
        <span style={{ color: C.line2 }}>”</span>
      </div>
      <div style={{ position: "absolute", left: 260, top: 700, fontFamily: F.body, fontSize: 30, color: C.ink2, opacity: firma }}>
        <b style={{ color: C.ink }}>Un cliente</b>, en una reseña de 5 estrellas en Google Maps
      </div>
      <div style={{ position: "absolute", left: 260, right: 160, top: 790, display: "flex", alignItems: "center", gap: 16, fontFamily: F.body, fontSize: 29, color: C.ink2, opacity: check }}>
        <Icon name="check" size={32} color={C.ok} />
        <span>En Carlos Paz, <b style={{ color: C.ink }}>cuatro de las cinco reseñas de 5 estrellas que muestra Google nombran a la misma vendedora.</b></span>
      </div>
      <Pie seccion="1 / 4" fuente="Fuente: sus fichas de Google Maps, textual y sin nombres, leídas el 11-nov-2026." />
    </AbsoluteFill>
  );
};

/** 6. Cierre en blanco: solo la pregunta, con el contacto de Atentina chico abajo. */
export const Cierre: React.FC = () => {
  const line = useIn(0.3, 0.7);
  const contacto = useIn(1.2, 0.6);
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

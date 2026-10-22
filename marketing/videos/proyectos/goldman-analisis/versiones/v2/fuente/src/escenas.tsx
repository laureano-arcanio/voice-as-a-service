import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

// Colores del PDF goldman-propuesta v1: verde para lo que hacen bien, naranja para lo observado
export const NAR = "#c2410c";
export const NAR_SOFT = "#fff4ed";

/** Pie de página como el del PDF: "Atentina · Isaías Goldman SA" y la sección. */
export const Pie: React.FC<{ fuente?: string; seccion: string }> = ({ fuente, seccion }) => {
  const o = useIn(0.6, 0.6);
  return (
    <div style={{
      position: "absolute", left: 120, right: 120, top: 1000, display: "flex", justifyContent: "space-between", gap: 40,
      fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: o, borderTop: `2px solid ${C.line}`, paddingTop: 14,
    }}>
      <span>{fuente ?? ""}</span>
      <span style={{ whiteSpace: "nowrap" }}>ATENTINA · ISAÍAS GOLDMAN SA · {seccion}</span>
    </div>
  );
};

const SECCIONES = ["Lo que ya hacen bien", "Lo que observamos", "Lo que dicen sus clientes", "La propuesta"];

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
        PROPUESTA · ISAÍAS GOLDMAN SA · OCTUBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 340, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 82,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Que cada consulta tenga respuesta,<br /><span style={{ color: C.accentOnDark }}>y que ustedes las vean todas.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 568, textAlign: "center", fontFamily: F.body, fontSize: 34, color: C.ctaMuted, opacity: sub }}>
        Atención 24/7 por teléfono, WhatsApp y web, con todo a la vista
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

type Dato = { cifra: string; chica?: boolean; texto: string; fuente: string; at: number; estrellas?: boolean };
// Momentos de a2 (s desde que arranca la voz), por las pausas de la toma
const DATOS: Dato[] = [
  { cifra: "30 años", texto: "En el rubro desde los 90, con tres generaciones de oficio en la familia.", fuente: "InfoNegocios (2018 y 2021)", at: 2.5 },
  { cifra: "4.500 m²", texto: "De casa en Bv. Bulnes y Pringles, con unas 50 personas.", fuente: "InfoNegocios (2018)", at: 3.95 },
  { cifra: "1.671 reseñas", texto: "En Google, con 4,2 de promedio.", fuente: "Google Maps, 21-oct-2026", at: 4.9, estrellas: true },
  { cifra: "Arcor, Georgalos, Mostaza", chica: true, texto: "Empresas que les compran, además del público y los instaladores.", fuente: "Su sitio", at: 5.6 },
];

const Estrellas: React.FC<{ p: number }> = ({ p }) => (
  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
    {[0, 1, 2, 3, 4].map((i) => {
      const lleno = Math.max(0, Math.min(1, p * 4.2 - i));
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
    <span style={{ fontFamily: F.mono, fontSize: 26, color: C.ink, marginLeft: 8 }}>{(4.2 * p).toFixed(1).replace(".", ",")}</span>
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
      <Headline eyebrow="Lo que ya hacen bien" text="En Isaías Goldman ya hicieron" accent="lo difícil." />
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
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: d.chica ? 58 : 76, lineHeight: 1.05, color: C.ink, letterSpacing: "-0.015em" }}>{d.cifra}</div>
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

const CITA = ["Nos", "gusta", "hacer", "cosas", "donde", "podemos", "responder."];

/** 1b. La cita de Isaías: la frase que une lo que hacen con lo que proponemos. */
export const Cita: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a3;
  const barra = useIn(0.15, 0.6);
  const firma = useIn(AT.a3 + 3.4, 0.6);
  const jonatan = useIn(AT.a3 + 4.0, 0.6);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 120, top: 76 }}>
        <div style={{ fontFamily: F.mono, fontSize: 24, letterSpacing: "0.08em", color: C.accent }}>LO QUE YA HACEN BIEN</div>
      </div>
      <div style={{ position: "absolute", left: 200, top: 300, width: 12, height: 420 * barra, borderRadius: 6, background: C.accent }} />
      <div style={{ position: "absolute", left: 260, right: 160, top: 300, fontFamily: F.display, fontWeight: 800, fontSize: 104, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.02em" }}>
        <span style={{ color: C.line2 }}>“</span>
        {CITA.map((w, i) => {
          const p = interpolate(t, [1.95 + i * 0.33, 2.3 + i * 0.33], [0, 1], { ...CLAMP, easing: EASE });
          const ult = i === CITA.length - 1;
          return (
            <span key={i} style={{ opacity: 0.12 + 0.88 * p, color: ult ? C.accent : C.ink }}>{w}{ult ? "" : " "}</span>
          );
        })}
        <span style={{ color: C.line2 }}>”</span>
      </div>
      <div style={{ position: "absolute", left: 260, top: 660, fontFamily: F.body, fontSize: 32, color: C.ink2, opacity: firma }}>
        <b style={{ color: C.ink }}>Isaías Goldman</b>, en InfoNegocios (2018)
      </div>
      <div style={{ position: "absolute", left: 260, top: 760, display: "flex", alignItems: "center", gap: 16, fontFamily: F.body, fontSize: 30, color: C.ink2, opacity: jonatan }}>
        <Icon name="check" size={32} color={C.ok} />
        Y Jonatan, en 2021: <i style={{ color: C.ink }}>“Nuestro fuerte es el postventa”.</i>
      </div>
      <Pie seccion="1 / 4" />
    </AbsoluteFill>
  );
};

const ChipOscuro: React.FC<{ p: number; icon: "phone" | "wa" | "web" | "chart"; children: React.ReactNode }> = ({ p, icon, children }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 12, borderRadius: 999, padding: "12px 26px", fontFamily: F.body, fontWeight: 600,
    fontSize: 28, background: "#16213a", color: C.ctaInk, border: "2px solid #23304d", transform: `scale(${p})`, opacity: Math.min(1, p * 1.5),
  }}>
    <Icon name={icon} size={28} color={C.accentOnDark} />
    {children}
  </div>
);

/** 5. Cierre: el piloto desde noviembre (la última página del PDF). */
export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const line = useIn(0.5, 0.7);
  const canales = [usePop(1.3), usePop(1.5), usePop(1.7), usePop(1.9)];
  const contacto = useIn(2.4, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 200, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 500 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PROPUESTA PARA ISAÍAS GOLDMAN SA · PILOTO DE 30 DÍAS
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 450, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 76, lineHeight: 1.1, color: C.ctaInk, opacity: line, transform: `translateY(${(1 - line) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        ¿Les parece que hagamos un piloto<br /><span style={{ color: C.accentOnDark }}>antes de que inicie la temporada?</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 710, display: "flex", justifyContent: "center", gap: 18 }}>
        <ChipOscuro p={canales[0]} icon="phone">0800 / 0810</ChipOscuro>
        <ChipOscuro p={canales[1]} icon="wa">WhatsApp</ChipOscuro>
        <ChipOscuro p={canales[2]} icon="web">Chat en la web</ChipOscuro>
        <ChipOscuro p={canales[3]} icon="chart">Panel</ChipOscuro>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 850, display: "flex", justifyContent: "center", alignItems: "center", gap: 30, opacity: contacto }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 16, padding: "16px 34px", fontFamily: F.body, fontWeight: 700, fontSize: 32 }}>
          Coordinemos el piloto
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 32, color: C.ctaMuted }}>atentina.com.ar · 0800-220-1233</div>
      </div>
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// Dónde podríamos mejorar con Atentina (PDF sqlamoblamientos-propuesta v1, página 2): las seis tarjetas condensadas en
// cuatro, azules, cada una con su oportunidad. Cada tarjeta entra con su frase:
// a4a "Dónde podríamos mejorar con Atentina." 0–2,27 · "Mientras espera," 2,63 · "el cliente pregunta cómo va lo suyo." 3,82
// a4b "La posventa" 0 · "entra como un mensaje más." 1,04 · a4c "Un solo WhatsApp," 0 · "para consultas de todo el país." 1,34
// a4d "Y la atención," 0,1 · "en horario reducido." 1,08–2,23 (v2; en v1, "Y una cocina se piensa de noche...")
// v4 (laura): "Mientras espera," 2,92 · "cómo va lo suyo" 5,26
const M = { espera: AT.a4a + 2.85, posventa: AT.a4b + 0.05, canales: AT.a4c + 0.05, horario: AT.a4d + 0.05 };
const CERRADO = "#c9d7ff";

const Tarjeta: React.FC<{
  x: number; y: number; p: number; op: number; rotulo: string; titulo: string; oportunidad: string; children: React.ReactNode;
}> = ({ x, y, p, op, rotulo, titulo, oportunidad, children }) => (
  <div style={{
    position: "absolute", left: x, top: y, width: 825, height: 344, boxSizing: "border-box", padding: "20px 34px",
    background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.accent}`, borderRadius: 24, boxShadow: shadowCard,
    opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
  }}>
    <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: C.muted }}>{rotulo}</div>
    <div style={{ fontFamily: F.display, fontWeight: 800, lineHeight: 1.12, color: C.ink, letterSpacing: "-0.01em", marginTop: 4, fontSize: 31 }}>{titulo}</div>
    <div style={{ height: 104, marginTop: 12, position: "relative" }}>{children}</div>
    <div style={{
      position: "absolute", left: 34, right: 34, bottom: 18, borderTop: `2px solid ${C.line}`, paddingTop: 10,
      fontFamily: F.body, fontSize: 22, lineHeight: 1.3, color: C.accent2, opacity: op,
    }}>
      <b>Oportunidad:</b> {oportunidad}
    </div>
  </div>
);

// El camino del mueble (PDF, página 1), desde el presupuesto: el cliente espera una noticia
const ETAPAS = ["Presupuesto", "Seña", "Fabricación · 90 a 100 días", "Instalación"];
// Mensajes de ejemplo que llegan al mismo WhatsApp (ilustrativos); el de posventa se resalta
const MENSAJES = [
  { t: "Quiero presupuestar una cocina", pos: false },
  { t: "¿Cómo va lo mío?", pos: false },
  { t: "Faltan colocar los zócalos", pos: true },
  { t: "¿Tienen local en Salta?", pos: false },
];
const ORIGENES = ["Sitio", "Instagram", "Linktree", "Showroom"];
const DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
// Horario de la casa central (sitio y Google Maps): lu a vie 9–13 y 14–18, sábados a la mañana (9–13): 44 h abiertas
const ABIERTO: [number, number][][] = [...Array(5).fill([[9, 13], [14, 18]]), [[9, 13]], []];

/** 2. Dónde podríamos mejorar con Atentina: cuatro oportunidades, una por frase. */
export const Mejorar: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const p = [useIn(M.espera, 0.6), useIn(M.posventa, 0.6), useIn(M.canales, 0.6), useIn(M.horario, 0.6)];
  const op = [useIn(M.espera + 2.0, 0.6), useIn(M.posventa + 1.6, 0.6), useIn(M.canales + 1.8, 0.6), useIn(M.horario + 1.3, 0.6)];
  // Tarjeta 1: la espera avanza por las etapas y el cliente pregunta con "cómo va lo suyo" (~3,9 s de a4a)
  const etapas = ETAPAS.map((_, i) => usePop(M.espera + 0.2 + i * 0.12));
  const avance = interpolate(t, [M.espera + 0.6, M.espera + 2.4], [0, 0.62], { ...CLAMP, easing: EASE });
  const pregunta = usePop(AT.a4a + 5.2);
  // Tarjeta 2: los mensajes entran juntos; con "un mensaje más" se resalta el de posventa
  const mensajes = MENSAJES.map((_, i) => usePop(M.posventa + 0.15 + i * 0.12));
  const resalta = interpolate(t, [AT.a4b + 1.2, AT.a4b + 1.6], [0, 1], CLAMP);
  // Tarjeta 3: los orígenes al único WhatsApp
  const origenes = ORIGENES.map((_, i) => interpolate(t, [M.canales + 0.2 + i * 0.1, M.canales + 0.5 + i * 0.1], [0, 1], CLAMP));
  const uno = usePop(M.canales + 0.7);
  const pais = useIn(AT.a4c + 1.4, 0.5);
  // Tarjeta 4: la semana se llena; el contador cuenta las horas abiertas
  const semana = interpolate(t, [M.horario + 0.2, M.horario + 1.4], [0, 1], CLAMP);
  const horas = Math.round(44 * semana);
  const W = 470;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Dónde podríamos mejorar con Atentina" text="El mueble ya está resuelto." accent="La oportunidad está en la espera." size={54} />

      <Tarjeta x={120} y={250} p={p[0]} op={op[0]} rotulo="PRESUPUESTOS Y FABRICACIÓN" titulo="Mientras espera, el cliente pregunta cómo va lo suyo"
        oportunidad="responderle al instante, con el dato de su pedido, en qué etapa está.">
        <div style={{ position: "absolute", left: 0, top: 50, width: 740, height: 8, borderRadius: 4, background: C.surface2 }} />
        <div style={{ position: "absolute", left: 0, top: 50, width: 740 * avance, height: 8, borderRadius: 4, background: C.accent }} />
        <div style={{ position: "absolute", left: 0, top: 30, width: 740, display: "flex", justifyContent: "space-between" }}>
          {ETAPAS.map((e, i) => (
            <div key={e} style={{
              borderRadius: 999, padding: "8px 14px", background: i === 2 ? C.accentSoft : "#fff", border: `2px solid ${i === 2 ? C.accent : C.line}`,
              fontFamily: F.body, fontWeight: 700, fontSize: 19, color: C.ink, whiteSpace: "nowrap",
              transform: `scale(${etapas[i]})`, opacity: Math.min(1, etapas[i] * 1.5),
            }}>{e}</div>
          ))}
        </div>
        <div style={{
          position: "absolute", left: 360, top: -16, borderRadius: 16, borderBottomLeftRadius: 4, padding: "6px 14px", background: C.wa,
          color: "#fff", fontFamily: F.body, fontWeight: 700, fontSize: 19, whiteSpace: "nowrap",
          transform: `scale(${pregunta})`, transformOrigin: "left bottom", opacity: Math.min(1, pregunta * 1.5),
        }}>¿cómo va lo mío?</div>
      </Tarjeta>

      <Tarjeta x={975} y={250} p={p[1]} op={op[1]} rotulo="POSVENTA" titulo="Un ajuste después de instalar, sin un lugar donde dejarlo"
        oportunidad="cada reclamo con número de caso, fotos, responsable y plazo de respuesta.">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, width: 757 }}>
          {MENSAJES.map((m, i) => {
            const on = m.pos ? resalta : 0;
            return (
              <div key={m.t} style={{
                display: "flex", alignItems: "center", gap: 10, height: 46, boxSizing: "border-box", padding: "0 14px", borderRadius: 14,
                background: on > 0.5 ? C.accentSoft : C.surface2, border: `2px solid ${on > 0.5 ? C.accent : "transparent"}`,
                transform: `scale(${mensajes[i] * (1 + 0.03 * on)})`, opacity: Math.min(1, mensajes[i] * 1.5) * (resalta > 0.5 && !m.pos ? 0.55 : 1),
              }}>
                <Icon name="wa" size={22} color={C.wa} />
                <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 20, color: C.ink, whiteSpace: "nowrap" }}>{m.t}</span>
              </div>
            );
          })}
        </div>
      </Tarjeta>

      <Tarjeta x={120} y={624} p={p[2]} op={op[2]} rotulo="CANALES Y RED" titulo="Un solo WhatsApp para todo lo digital, y 20 puntos de venta"
        oportunidad="un número para todo el país que pase cada consulta al local de la zona.">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, width: 300 }}>
          {ORIGENES.map((x, i) => (
            <div key={x} style={{
              borderRadius: 999, padding: "6px 14px", background: C.surface2, fontFamily: F.body, fontWeight: 600, fontSize: 20, color: C.ink2,
              opacity: origenes[i], transform: `translateX(${(1 - origenes[i]) * -20}px)`,
            }}>{x}</div>
          ))}
        </div>
        <svg width={70} height={40} style={{ position: "absolute", left: 300, top: 30 }}>
          <path d="M4 20 H52 M40 8 L56 20 L40 32" stroke={C.accent} strokeWidth={4} fill="none" strokeLinecap="round" opacity={uno} />
        </svg>
        <div style={{
          position: "absolute", left: 380, top: 18, display: "flex", alignItems: "center", gap: 10, width: 250, height: 62, boxSizing: "border-box",
          padding: "0 16px", borderRadius: 14, background: C.accentSoft, border: `2px solid ${C.accent}`, transform: `scale(${uno})`, opacity: Math.min(1, uno * 1.5),
        }}>
          <Icon name="wa" size={28} color={C.wa} />
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, whiteSpace: "nowrap" }}>Un solo WhatsApp</span>
        </div>
        <div style={{ position: "absolute", left: 645, top: 20, width: 115, fontFamily: F.mono, fontSize: 16, lineHeight: 1.3, color: C.muted, opacity: pais }}>
          consultas de todo el país
        </div>
      </Tarjeta>

      <Tarjeta x={975} y={624} p={p[3]} op={op[3]} rotulo="HORARIO REDUCIDO" titulo="Atención en horario reducido: 44 de las 168 horas"
        oportunidad="responder también fuera de horario y dejar la visita o la medición agendada.">
        <div style={{ position: "relative" }}>
          {DIAS.map((d, i) => (
            <div key={d} style={{ display: "flex", alignItems: "center", gap: 10, height: 14, marginBottom: 1 }}>
              <span style={{ width: 30, fontFamily: F.mono, fontSize: 12, color: C.muted }}>{d}</span>
              <div style={{ position: "relative", width: W, height: 11, borderRadius: 4, background: C.surface2, overflow: "hidden" }}>
                <div style={{ position: "absolute", left: 0, top: 0, height: 11, width: W * semana, background: CERRADO }} />
                {ABIERTO[i].map(([a, b]) => (
                  <div key={a} style={{ position: "absolute", left: (a / 24) * W, width: ((b - a) / 24) * W * semana, top: 0, height: 11, background: C.ok }} />
                ))}
              </div>
            </div>
          ))}
          <div style={{ position: "absolute", left: 530, top: 0, whiteSpace: "nowrap" }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 56, color: C.accent, fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{horas} hs</div>
            <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 6 }}>abierto, de 168</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 6 }}>
              <span style={{ width: 13, height: 13, borderRadius: 3, background: C.ok }} />abierto
              <span style={{ width: 13, height: 13, borderRadius: 3, background: CERRADO, marginLeft: 8 }} />cerrado
            </div>
          </div>
        </div>
      </Tarjeta>

      <Pie seccion="2 / 4" fuente="Fuentes: su sitio, Google Maps e InfoNegocios (abril de 2025), leídos el 22-oct-2026. Mensajes de ejemplo." />
    </AbsoluteFill>
  );
};

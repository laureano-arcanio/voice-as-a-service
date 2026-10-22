import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// Áreas a mejorar (PDF baicenter-propuesta v1, página 1): tarjetas azules, cada una con su oportunidad.
// Cada tarjeta entra con su frase; a4a dice "Dónde podríamos mejorar con Atentina." y "Dos WhatsApp" arranca a ~2,8 s.
const M = { canales: AT.a4a + 2.7, horario: AT.a4b + 0.1, fin: AT.a4c + 0.1, mercado: AT.a4d + 0.1 };
const CERRADO = "#c9d7ff";

const Tarjeta: React.FC<{
  x: number; y: number; p: number; op: number; rotulo: string; titulo: string; oportunidad: string; children: React.ReactNode; chico?: boolean;
}> = ({ x, y, p, op, rotulo, titulo, oportunidad, children, chico }) => (
  <div style={{
    position: "absolute", left: x, top: y, width: 825, height: 344, boxSizing: "border-box", padding: "22px 34px",
    background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${C.accent}`, borderRadius: 24, boxShadow: shadowCard,
    opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
  }}>
    <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: C.muted }}>{rotulo}</div>
    <div style={{ fontFamily: F.display, fontWeight: 800, lineHeight: 1.12, color: C.ink, letterSpacing: "-0.01em", marginTop: 4, whiteSpace: chico ? "normal" : "nowrap", fontSize: chico ? 31 : 35 }}>{titulo}</div>
    <div style={{ height: chico ? 100 : 132, marginTop: chico ? 10 : 12, position: "relative" }}>{children}</div>
    <div style={{
      position: "absolute", left: 34, right: 34, bottom: 20, borderTop: `2px solid ${C.line}`, paddingTop: 10,
      fontFamily: F.body, fontSize: 22, lineHeight: 1.3, color: C.accent2, opacity: op,
    }}>
      <b>Oportunidad:</b> {oportunidad}
    </div>
  </div>
);

const TEMAS = ["BAIC", "Arcfox", "Mitsubishi", "Foton", "Ventas", "Posventa", "Repuestos", "Flotas"];
const LINEAS = ["WhatsApp 1", "WhatsApp 2", "Teléfono fijo"];
const DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
// Horario publicado de BAIC, Arcfox y MitsuCenter: lu a vie de 9 a 20, sáb de 9 a 13, dom cerrado (59 h abiertas)
const ABIERTO: [number, number][][] = [...Array(5).fill([[9, 20]]), [[9, 13]], []];
// Financiación (verificada por el usuario, 22-oct-2026): Bancor, Banco Nación, Santander y Galicia, y crédito propio.
const PREGUNTAS = ["¿Cuánto queda la cuota?", "¿Con qué banco?", "¿Toman mi usado?"];

/** 2. Áreas a mejorar: cuatro oportunidades que se ven desde afuera. */
export const Areas: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const p = [useIn(M.canales, 0.6), useIn(M.horario, 0.6), useIn(M.fin, 0.6), useIn(M.mercado, 0.6)];
  const op = [useIn(M.canales + 1.6, 0.6), useIn(M.horario + 1.6, 0.6), useIn(M.fin + 1.6, 0.6), useIn(M.mercado + 2.3, 0.6)];
  const temas = TEMAS.map((_, i) => interpolate(t, [M.canales + 0.2 + i * 0.09, M.canales + 0.5 + i * 0.09], [0, 1], CLAMP));
  const lineas = LINEAS.map((_, i) => usePop(M.canales + 0.9 + i * 0.12));
  const semana = interpolate(t, [M.horario + 0.2, M.horario + 1.4], [0, 1], CLAMP);
  const horas = Math.round(109 * semana);
  const preguntas = PREGUNTAS.map((_, i) => usePop(M.fin + 0.3 + i * 0.35));
  const cliente = usePop(M.mercado + 0.2);
  const locales = [usePop(M.mercado + 0.6), usePop(M.mercado + 0.8)];
  // "la primera respuesta decide" arranca a ~2,8 s de a4d
  const primera = interpolate(t, [M.mercado + 2.7, M.mercado + 3.2], [0, 1], { ...CLAMP, easing: EASE });
  const W = 470;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Dónde podríamos mejorar con Atentina" text="Oportunidades para" accent="vender más con el mismo equipo." size={58} />

      <Tarjeta x={120} y={250} p={p[0]} op={op[0]} rotulo="CANALES" titulo="Dos WhatsApp y un fijo para todo el grupo"
        oportunidad="que cada consulta llegue clasificada a la marca y al vendedor que corresponde.">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, width: 440 }}>
          {TEMAS.map((x, i) => (
            <div key={x} style={{
              borderRadius: 999, padding: "6px 14px", background: C.surface2, fontFamily: F.body, fontWeight: 600, fontSize: 20, color: C.ink2,
              opacity: temas[i], transform: `translateX(${(1 - temas[i]) * -20}px)`,
            }}>{x}</div>
          ))}
        </div>
        <svg width={60} height={40} style={{ position: "absolute", left: 455, top: 46 }}>
          <path d="M4 20 H46 M34 8 L50 20 L34 32" stroke={C.accent} strokeWidth={4} fill="none" strokeLinecap="round" opacity={lineas[0]} />
        </svg>
        <div style={{ position: "absolute", left: 525, top: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          {LINEAS.map((l, i) => (
            <div key={l} style={{
              display: "flex", alignItems: "center", gap: 10, width: 220, height: 38, boxSizing: "border-box", padding: "0 14px", borderRadius: 12,
              background: C.accentSoft, border: `2px solid ${C.accent}`, transform: `scale(${lineas[i]})`, opacity: Math.min(1, lineas[i] * 1.5),
            }}>
              <Icon name={i < 2 ? "wa" : "phone"} size={22} color={i < 2 ? C.wa : C.accent} />
              <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 20, color: C.ink, whiteSpace: "nowrap" }}>{l}</span>
            </div>
          ))}
        </div>
      </Tarjeta>

      <Tarjeta x={975} y={250} p={p[1]} op={op[1]} rotulo="HORARIO" titulo="109 de 168 horas, el showroom cerrado"
        oportunidad="que esas consultas tengan respuesta en el momento y un turno para el lunes.">
        <div style={{ position: "relative" }}>
          {DIAS.map((d, i) => (
            <div key={d} style={{ display: "flex", alignItems: "center", gap: 10, height: 18, marginBottom: 1 }}>
              <span style={{ width: 30, fontFamily: F.mono, fontSize: 14, color: C.muted }}>{d}</span>
              <div style={{ position: "relative", width: W, height: 13, borderRadius: 4, background: C.surface2, overflow: "hidden" }}>
                <div style={{ position: "absolute", left: 0, top: 0, height: 13, width: W * semana, background: CERRADO }} />
                {ABIERTO[i].map(([a, b]) => (
                  <div key={a} style={{ position: "absolute", left: (a / 24) * W, width: ((b - a) / 24) * W, top: 0, height: 13, background: C.ok }} />
                ))}
              </div>
            </div>
          ))}
          <div style={{ position: "absolute", left: 530, top: 4, whiteSpace: "nowrap" }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, color: C.accent, fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{horas} hs</div>
            <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 8 }}>de las 168 de la semana</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 8 }}>
              <span style={{ width: 13, height: 13, borderRadius: 3, background: C.ok }} />abierto
              <span style={{ width: 13, height: 13, borderRadius: 3, background: CERRADO, marginLeft: 8 }} />cerrado
            </div>
          </div>
        </div>
      </Tarjeta>

      <Tarjeta x={120} y={624} p={p[2]} op={op[2]} rotulo="FINANCIACIÓN" titulo="Cuatro bancos y crédito propio: muchas preguntas antes de venir" chico
        oportunidad="responderlas al instante y que el vendedor reciba al interesado con la forma de pago encaminada.">
        <div style={{ display: "flex", gap: 10, width: 740 }}>
          {PREGUNTAS.map((q, i) => (
            <div key={q} style={{
              borderRadius: 18, borderBottomLeftRadius: 4, padding: "10px 16px", background: C.surface2,
              fontFamily: F.body, fontWeight: 600, fontSize: 21, color: C.ink, whiteSpace: "nowrap",
              transform: `scale(${preguntas[i]})`, transformOrigin: "left bottom", opacity: Math.min(1, preguntas[i] * 1.5),
            }}>{q}</div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 14, opacity: preguntas[2] }}>
          {["Bancor", "Banco Nación", "Santander", "Galicia", "Crédito propio"].map((b) => (
            <div key={b} style={{ borderRadius: 999, padding: "4px 12px", border: `2px solid ${C.line}`, fontFamily: F.mono, fontSize: 15, color: C.ink2, whiteSpace: "nowrap" }}>{b}</div>
          ))}
        </div>
      </Tarjeta>

      <Tarjeta x={975} y={624} p={p[3]} op={op[3]} rotulo="MERCADO" titulo="Dos concesionarios BAIC en Córdoba"
        oportunidad="ser el que contesta primero y mejor: la primera respuesta suele decidir la visita.">
        <svg width={760} height={132} style={{ position: "absolute", left: 0, top: 0 }}>
          {[28, 104].map((y, i) => (
            <path key={y} d={`M190 66 C 260 66, 260 ${y}, 330 ${y}`} stroke={i === 0 && primera > 0.5 ? C.accent : C.line2} strokeWidth={4}
              strokeDasharray="8 8" fill="none" opacity={locales[i]} />
          ))}
        </svg>
        <div style={{
          position: "absolute", left: 0, top: 26, width: 190, height: 80, boxSizing: "border-box", display: "flex", alignItems: "center", gap: 10,
          padding: "0 14px", borderRadius: 16, background: C.surface2, transform: `scale(${cliente})`,
        }}>
          <Icon name="users" size={30} color={C.ink2} />
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 20, color: C.ink, lineHeight: 1.1 }}>El mismo<br />cliente</span>
        </div>
        {[0, 1].map((i) => {
          const on = i === 0 ? primera : 0;
          return (
            <div key={i} style={{
              position: "absolute", left: 330, top: i === 0 ? 4 : 80, width: 250, height: 48, boxSizing: "border-box", display: "flex", alignItems: "center",
              gap: 10, padding: "0 14px", borderRadius: 12, background: on > 0.5 ? C.accentSoft : "#fff",
              border: `2px solid ${on > 0.5 ? C.accent : C.line}`, transform: `scale(${locales[i] * (1 + 0.04 * on)})`,
            }}>
              <Icon name="store" size={24} color={on > 0.5 ? C.accent : C.muted} />
              <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 20, color: C.ink, whiteSpace: "nowrap" }}>Concesionario BAIC</span>
            </div>
          );
        })}
        <div style={{
          position: "absolute", left: 596, top: 6, display: "flex", alignItems: "center", gap: 6, borderRadius: 999, padding: "8px 14px",
          background: C.accent, color: "#fff", fontFamily: F.body, fontWeight: 700, fontSize: 18, whiteSpace: "nowrap",
          opacity: primera, transform: `translateX(${(1 - primera) * -16}px)`,
        }}>
          <Icon name="check" size={20} color="#fff" />1ª respuesta
        </div>
      </Tarjeta>

      <Pie seccion="2 / 4" fuente="Fuentes: sus cuatro sitios, Google Maps y prensa de Córdoba (2026), leídos el 20-oct-2026." />
    </AbsoluteFill>
  );
};

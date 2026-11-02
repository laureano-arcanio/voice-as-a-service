import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Wave, useIn } from "../../../src/comun/ui";
import { Pie, useT } from "./escenas";
import { AT } from "./timeline";

// Ficha y minuta del PDF v2, página 3, con sus datos inventados. Momentos de a5a: "Sus clientes se cargan en la misma
// plataforma," 0,1 · "con teléfono," 2,45 · "suscripción" 3,35 · "y cuidados." 4,2. De a5b: "Antes de atender, su equipo
// oye una minuta." 0,1 · "Quien llama," 2,75 · "no la oye." 3,45
const FILAS = [
  { tel: "11 5555-0142", cli: "Laura Gómez, hija de Marta", sus: "Activa", cui: "24 h en domicilio" },
  { tel: "11 5555-0187", cli: "Carlos Ríos", sus: "Activa", cui: "Noches en sanatorio" },
  { tel: "11 5555-0123", cli: "Elena Suárez", sus: "Activa", cui: "Silver, dos veces por semana" },
  { tel: "11 5555-0165", cli: "Julia Paz", sus: "Sin abono", cui: "Guardia puntual" },
];
const COLS = "175px 335px 135px 1fr";
const MINUTA = "Laura Gómez, hija de Marta. Marta tiene cuidado 24 horas en domicilio, suscripción activa. Pide cambiar el turno de mañana. Marcá 1 para atender.".split(" ");

const Rotulo: React.FC<{ izq: string; der: string }> = ({ izq, der }) => (
  <div style={{ background: C.accentSoft, borderBottom: `2px solid #c9d6fb`, fontFamily: F.mono, fontSize: 19, letterSpacing: "0.04em", padding: "12px 24px", display: "flex", justifyContent: "space-between", color: C.accent2 }}>
    <span>{izq}</span><span style={{ color: C.accent }}>{der}</span>
  </div>
);

/** 5. La ficha y la minuta: la minuta es para su equipo; quien llama no oye la ficha. */
export const Ficha: React.FC = () => {
  const t = useT();
  const a = (s: number) => AT.a5a + s;
  const b = (s: number) => AT.a5b + s;
  const tabla = useIn(a(0), 0.5);
  const filas = FILAS.map((_, i) => interpolate(t, [a(0.5 + i * 0.35), a(0.85 + i * 0.35)], [0, 1], { ...CLAMP, easing: EASE }));
  const col = (x: number) => Math.min(interpolate(t, [a(x), a(x + 0.2)], [0, 1], CLAMP), interpolate(t, [AT.a5b, AT.a5b + 0.3], [1, 0.0], CLAMP));
  const tel = col(2.45);
  const sus = col(3.35);
  const cui = col(4.2);
  const fila1 = interpolate(t, [b(0), b(0.3)], [0, 1], CLAMP);
  const minuta = useIn(b(0), 0.5);
  const palabras = interpolate(t, [b(0.2), b(2.7)], [0, MINUTA.length], CLAMP);
  const nollama = useIn(b(1.7), 0.5);
  const fuerte = interpolate(t, [b(2.75), b(3.05)], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Ficha de clientes y minuta" text="Sus clientes en la plataforma," accent="y su equipo sabe quién es." size={58} />

      <div style={{ position: "absolute", left: 120, top: 212, width: 1090, borderRadius: 22, overflow: "hidden", background: "#fff", border: `2px solid ${C.line2}`, boxShadow: shadowCard, opacity: tabla, transform: `translateY(${(1 - tabla) * 24}px)` }}>
        <Rotulo izq="CLIENTES · SIM TE CUIDA" der="EJEMPLO CON DATOS INVENTADOS" />
        <div style={{ display: "grid", gridTemplateColumns: COLS, padding: "12px 24px", borderBottom: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.muted }}>
          <span style={{ color: tel > 0.5 ? C.accent : C.muted }}>Teléfono</span><span>Cliente</span>
          <span style={{ color: sus > 0.5 ? C.accent : C.muted }}>Suscripción</span>
          <span style={{ color: cui > 0.5 ? C.accent : C.muted }}>Cuidados que recibe</span>
        </div>
        {FILAS.map((r, i) => {
          const f1 = i === 0 ? fila1 : 0;
          return (
            <div key={r.tel} style={{
              display: "grid", gridTemplateColumns: COLS, alignItems: "center", height: 72, padding: "0 24px", borderBottom: i < 3 ? `2px solid ${C.line}` : "none",
              fontFamily: F.body, fontSize: 24, color: C.ink, opacity: filas[i], background: f1 > 0.5 ? C.accentSoft : "transparent",
            }}>
              <span style={{ fontFamily: F.mono, fontSize: 22, color: tel > 0.5 ? C.accent : C.ink }}>{r.tel}</span>
              <span style={{ fontWeight: 700 }}>{r.cli}</span>
              <span>
                <span style={{ padding: "3px 12px", borderRadius: 999, fontSize: 20, fontWeight: 700, background: r.sus === "Activa" ? C.okSoft : C.surface2, color: r.sus === "Activa" ? "#11734a" : C.ink2, whiteSpace: "nowrap", outline: sus > 0.5 ? `2px solid ${C.accent}` : "none" }}>{r.sus}</span>
              </span>
              <span style={{ color: cui > 0.5 ? C.accent : C.ink2, fontWeight: cui > 0.5 ? 700 : 400 }}>{r.cui}</span>
            </div>
          );
        })}
      </div>

      <div style={{ position: "absolute", left: 120, top: 648, width: 1090, fontFamily: F.body, fontSize: 26, lineHeight: 1.3, color: C.ink2, opacity: filas[3] }}>
        La carga es de ustedes, y el arranque lo hacemos juntos: <b style={{ color: C.ink }}>la carga inicial está incluida.</b> Suma DNI, otro contacto y los campos que definamos.
      </div>

      <div style={{ position: "absolute", left: 1240, top: 212, width: 560, height: 500, boxSizing: "border-box", borderRadius: 22, overflow: "hidden", background: "#fff", border: `2px solid ${C.accent}`, boxShadow: shadowCard, opacity: minuta, transform: `translateX(${(1 - minuta) * 30}px)` }}>
        <Rotulo izq="LA MINUTA, ANTES DE ATENDER" der="" />
        <div style={{ padding: "22px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
            <Icon name="ear" size={36} color={C.accent} />
            <Wave n={9} h={30} color={C.accent} live={palabras < MINUTA.length ? 1 : 0.1} />
          </div>
          <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 31, lineHeight: 1.3, color: C.ink }}>
            {MINUTA.map((w, i) => <span key={i} style={{ opacity: i < palabras ? 1 : 0.12 }}>{w} </span>)}
          </div>
          <div style={{ fontFamily: F.mono, fontSize: 18, color: C.muted, marginTop: 16 }}>EJEMPLO CON DATOS INVENTADOS</div>
          <div style={{ fontFamily: F.body, fontSize: 24, color: C.ink2, marginTop: 10 }}>Por WhatsApp, el aviso lleva la misma minuta.</div>
        </div>
      </div>

      <div style={{
        position: "absolute", left: 120, right: 120, top: 760, height: 210, boxSizing: "border-box", padding: "20px 36px", display: "flex", alignItems: "center", gap: 34, borderRadius: 24,
        background: fuerte > 0.5 ? C.accentSoft : "#fff", border: `3px solid ${fuerte > 0.5 ? C.accent : C.line}`, opacity: nollama, transform: `translateY(${(1 - nollama) * 20}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 46, lineHeight: 1.08, color: C.ink, width: 620, flexShrink: 0 }}>
          Quien llama <span style={{ color: C.accent }}>no oye la ficha.</span>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 29, lineHeight: 1.3, color: C.ink2 }}>
          La minuta y los cuidados son para su equipo: el agente no se los lee a quien llama, que puede ser un familiar.
        </div>
      </div>

      <Pie fuente="Son datos de salud, y por eso sensibles: el tratamiento y la retención se acuerdan antes de la salida en vivo." />
    </AbsoluteFill>
  );
};

// Panel del PDF v2, página 4, con sus números ilustrativos. Momentos de a6: "En el panel ven" 0,1 · "quién tomó cada consulta," 1,0 · "y cuánto tardó." 2,6
const KPIS = [
  { n: 186, sufijo: "", t: "consultas, entre llamadas y WhatsApp" },
  { n: 78, sufijo: "", t: "derivadas a su equipo; 108 resueltas por el agente" },
  { n: 5, sufijo: "", t: "posibles emergencias priorizadas; una persona en 52 s" },
];
const PERSONAS = [
  { q: "Persona 1", rec: 21, tomo: "18 s", pasa: 0, em: 2 },
  { q: "Persona 2", rec: 20, tomo: "31 s", pasa: 2, em: 1 },
  { q: "Persona 3", rec: 19, tomo: "22 s", pasa: 1, em: 1 },
  { q: "Persona 4", rec: 18, tomo: "47 s", pasa: 3, em: 1 },
];
const COLS_P = "1.4fr 1fr 1fr 1.2fr 1fr";

/** 6. El panel: pocas cifras, quién tomó cada consulta y cuánto tardó (datos ilustrativos). */
export const Panel: React.FC = () => {
  const t = useT();
  const v = (s: number) => AT.a6 + s;
  const panel = useIn(v(0), 0.5);
  const k = interpolate(t, [v(0.2), v(1.1)], [0, 1], { ...CLAMP, easing: EASE });
  const quien = interpolate(t, [v(1.0), v(1.3)], [0, 1], CLAMP);
  const tardo = interpolate(t, [v(2.6), v(2.9)], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Para quien dirige" text="Toda la atención a la vista:" accent="quién la tomó y cuánto tardó." size={58} />
      <div style={{ position: "absolute", left: 120, top: 212, width: 1680, height: 762, borderRadius: 24, overflow: "hidden", border: `2px solid ${C.line2}`, background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.10)", opacity: panel, transform: `translateY(${(1 - panel) * 50}px)` }}>
        <div style={{ background: C.accentSoft, borderBottom: "2px solid #c9d6fb", fontFamily: F.mono, fontSize: 22, letterSpacing: "0.05em", padding: "14px 30px", display: "flex", justifyContent: "space-between", color: C.accent2 }}>
          <span>PANEL · SIM TE CUIDA</span><span style={{ color: C.accent }}>EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA</span>
        </div>
        <div style={{ background: C.bg2, padding: 22, height: 690, boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", gap: 18 }}>
            {KPIS.map((x) => (
              <div key={x.t} style={{ flex: 1, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 16, padding: "12px 24px", height: 158, boxSizing: "border-box" }}>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, color: C.accent, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>{Math.round(x.n * k)}{x.sufijo}</div>
                <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.2, color: C.ink2, marginTop: 4 }}>{x.t}</div>
              </div>
            ))}
          </div>
          <div style={{ flex: 1, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "16px 30px", boxSizing: "border-box" }}>
            <div style={{ fontFamily: F.mono, fontSize: 19, letterSpacing: "0.08em", color: C.muted }}>QUIÉN TOMÓ CADA CONSULTA, POR ROTACIÓN (MEDIANA)</div>
            <div style={{ display: "grid", gridTemplateColumns: COLS_P, marginTop: 10, paddingBottom: 8, borderBottom: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 700, fontSize: 25, color: C.muted }}>
              <span style={{ color: quien > 0.5 ? C.accent : C.muted }}>Persona</span><span style={{ textAlign: "right" }}>Recibió</span>
              <span style={{ textAlign: "right", color: tardo > 0.5 ? C.accent : C.muted }}>La tomó en</span>
              <span style={{ textAlign: "right" }}>Pasó a la siguiente</span><span style={{ textAlign: "right" }}>Emergencias</span>
            </div>
            {PERSONAS.map((r) => (
              <div key={r.q} style={{ display: "grid", gridTemplateColumns: COLS_P, alignItems: "center", height: 88, borderBottom: `2px solid ${C.line}`, fontFamily: F.mono, fontSize: 30, color: C.ink, opacity: k }}>
                <span style={{ fontFamily: F.body, fontWeight: 700, color: quien > 0.5 ? C.accent : C.ink }}>{r.q}</span>
                <span style={{ textAlign: "right" }}>{r.rec}</span>
                <span style={{ textAlign: "right", color: tardo > 0.5 ? C.accent : C.ink, fontWeight: tardo > 0.5 ? 700 : 500 }}>{r.tomo}</span>
                <span style={{ textAlign: "right" }}>{r.pasa}</span>
                <span style={{ textAlign: "right" }}>{r.em}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <Pie fuente="Las cifras del ejemplo son ilustrativas: muestran qué se mide, no un resultado ni un volumen esperado." />
    </AbsoluteFill>
  );
};

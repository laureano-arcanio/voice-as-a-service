import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/sqlamoblamientos-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Link, useIn, usePop } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// La propuesta en dos escenas, como goldman-analisis v3: el asesor de guardia (diagrama del PDF, página 3) y el panel
// (página 4). Momentos de a6a (s desde que arranca la voz), por las pausas de la toma:
// "Un asesor de guardia en su WhatsApp, su línea y su sitio." 0,1–3,3 · "Clasifica cada consulta" 3,64 ·
// "y la pasa a su equipo," 5,26 · "sobre todo a Ventas:" 6,66 · "al asesor," 8,23 · "o a la franquicia de la zona." 9,14–10,46
const M = { wa: 1.2, linea: 2.1, sitio: 2.7, clasifica: 3.64, deriva: 5.26, ventas: 6.7, asesor: 8.23, franquicia: 9.14 };

type IconoCanal = "phone" | "wa" | "web";
const CANALES: { icon: IconoCanal; titulo: string; y: number; at: number }[] = [
  { icon: "wa", titulo: "WhatsApp central", y: 330, at: M.wa },
  { icon: "phone", titulo: "Línea de la casa", y: 446, at: M.linea },
  { icon: "web", titulo: "Su sitio web", y: 562, at: M.sitio },
];
// Tipos de consulta y áreas de su equipo (diagrama del PDF, página 3)
const TIPOS = ["Proyecto", "Presupuesto", "Pedido", "Reclamo", "Pagos", "Otra zona"];
const AREAS = [
  { titulo: "Ventas", y: 300, h: 170 },
  { titulo: "Producción", y: 490, h: 80 },
  { titulo: "Administración", y: 586, h: 80 },
  { titulo: "Posventa", y: 682, h: 80 },
];

type P = { x: number; y: number };
const bez = (a: P, c: P, b: P, k: number): P => ({
  x: (1 - k) * (1 - k) * a.x + 2 * (1 - k) * k * c.x + k * k * b.x,
  y: (1 - k) * (1 - k) * a.y + 2 * (1 - k) * k * c.y + k * k * b.y,
});
type Curva = { a: P; b: P; c: P; d: string };
const curva = (a: P, b: P): Curva => {
  const c = { x: (a.x + b.x) / 2, y: a.y };
  return { a, b, c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` };
};
const AG = { x: 930, y: 470 };
const AREA_X = 1340;
const ENTRADAS = CANALES.map((c) => curva({ x: 520, y: c.y + 46 }, { x: AG.x - 100, y: AG.y }));
const SALIDAS = AREAS.map((a) => curva({ x: AG.x + 100, y: AG.y }, { x: AREA_X, y: a.y + a.h / 2 }));

const COLOR: Record<IconoCanal, string> = { phone: C.accent, wa: C.wa, web: C.accent2 };

const Paquete: React.FC<{ k: Curva; t0: number; t1: number; icon: IconoCanal }> = ({ k, t0, t1, icon }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const u = interpolate(t, [t0, t1], [0, 1], { ...CLAMP, easing: EASE });
  const o = interpolate(t, [t0 - 0.1, t0, t1, t1 + 0.25], [0, 1, 1, 0], CLAMP);
  const p = bez(k.a, k.c, k.b, u);
  return (
    <div style={{
      position: "absolute", left: p.x - 26, top: p.y - 26, width: 52, height: 52, borderRadius: 26, opacity: o,
      background: COLOR[icon], display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 22px rgba(36,86,230,.35)",
    }}>
      <Icon name={icon} size={26} color="#fff" />
    </div>
  );
};

/** 4a. La propuesta: el asesor de guardia en sus canales, que clasifica y pasa cada consulta a su equipo (sobre todo, Ventas). */
export const Propuesta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a6a + s;
  const agente = usePop(v(0.2));
  const canales = CANALES.map((c) => useIn(v(c.at), 0.5));
  const tipos = TIPOS.map((_, i) => usePop(v(M.clasifica + 0.15 + i * 0.12)));
  const areas = AREAS.map((_, i) => useIn(v(M.deriva + i * 0.12), 0.5));
  const nota = useIn(v(M.franquicia + 0.4), 0.6);
  const ventas = interpolate(t, [v(M.ventas), v(M.ventas + 0.4)], [0, 1], { ...CLAMP, easing: EASE });
  const asesor = interpolate(t, [v(M.asesor), v(M.asesor + 0.3)], [0, 1], CLAMP);
  const franquicia = interpolate(t, [v(M.franquicia), v(M.franquicia + 0.3)], [0, 1], CLAMP);
  const env = envs.a6a;
  const i = frame - Math.round(v(0) * fps);
  const talk = i >= 0 && i < env.length ? env[i] * 0.6 : 0;
  const SUBS = [
    { t: "Asesores y locales", on: asesor },
    { t: "Franquicia de la zona", on: franquicia },
  ];
  return (
    <AbsoluteFill>
      <Headline eyebrow="La propuesta" text="Un asesor de guardia," accent="en sus mismos canales." out={v(M.clasifica)} />
      <Headline eyebrow="La propuesta" text="Clasifica cada consulta y la pasa" accent="a su equipo." at={v(M.clasifica + 0.2)} />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRADAS.map((e, n) => <Link key={n} d={e.d} color={C.accent} opacity={canales[n] * 0.5} />)}
        {SALIDAS.map((e, n) => (
          <Link key={n} d={e.d} color={C.accent} opacity={areas[n] * (n === 0 ? 0.5 + 0.4 * ventas : 0.5 - 0.25 * ventas)} width={n === 0 ? 5 + 3 * ventas : 5} />
        ))}
      </svg>

      {CANALES.map((c, n) => (
        <div key={c.titulo} style={{
          position: "absolute", left: 120, top: c.y, width: 400, height: 92, boxSizing: "border-box", padding: "0 24px",
          display: "flex", alignItems: "center", gap: 16, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 20, boxShadow: shadowCard,
          opacity: canales[n], transform: `translateX(${(1 - canales[n]) * -40}px)`,
        }}>
          <div style={{ width: 56, height: 56, borderRadius: 28, background: c.icon === "wa" ? C.okSoft : C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name={c.icon} size={30} color={c.icon === "wa" ? C.wa : C.accent} />
          </div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 31, color: C.ink, whiteSpace: "nowrap" }}>{c.titulo}</div>
        </div>
      ))}

      <div style={{ position: "absolute", left: AG.x - 100, top: AG.y - 100, width: 200, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente})` }}>
        <AgenteLogo size={200} talk={talk} style={{ filter: "drop-shadow(0 16px 30px rgba(36,86,230,.22))" }} />
        <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 20, whiteSpace: "nowrap" }}>
          Asesor de guardia · 24/7
        </div>
      </div>

      {/* Clasifica: los tipos de consulta del PDF */}
      <div style={{ position: "absolute", left: AG.x - 400, width: 800, top: 690, display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 12 }}>
        {TIPOS.map((x, n) => (
          <div key={x} style={{
            borderRadius: 999, padding: "10px 22px", fontFamily: F.body, fontWeight: 700, fontSize: 25, whiteSpace: "nowrap",
            background: C.accentSoft, color: C.accent2, transform: `scale(${tipos[n]})`, opacity: Math.min(1, tipos[n] * 1.5),
          }}>{x}</div>
        ))}
      </div>

      {/* Su equipo, por área; Ventas toma el acento con "sobre todo a Ventas" y se marcan el asesor y la franquicia */}
      <div style={{ position: "absolute", left: AREA_X, top: 252, fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted, opacity: areas[0] }}>
        SU EQUIPO
      </div>
      {AREAS.map((a, n) => {
        const top = n === 0;
        const p = areas[n];
        const e = top ? ventas : 0;
        return (
          <div key={a.titulo} style={{
            position: "absolute", left: AREA_X, top: a.y, width: 460, height: a.h, boxSizing: "border-box", padding: top ? "18px 26px" : "0 26px",
            display: "flex", alignItems: top ? "flex-start" : "center", gap: 16, borderRadius: 20,
            background: top ? (e > 0.5 ? C.accentSoft : "#fff") : "#fff",
            border: `${top ? 3 : 2}px solid ${e > 0.5 ? C.accent : C.line}`,
            boxShadow: e > 0.05 ? `0 0 0 ${8 * e}px rgba(36,86,230,.12), ${shadowCard}` : shadowCard,
            opacity: p * (top ? 1 : 1 - 0.35 * ventas), transform: `translateX(${(1 - p) * 40}px) scale(${1 + 0.05 * e})`, transformOrigin: "left center",
          }}>
            <div style={{ marginTop: top ? 4 : 0 }}><Icon name="users" size={top ? 36 : 28} color={C.accent} /></div>
            <div>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: top ? 40 : 29, color: e > 0.5 ? C.accent : C.ink, lineHeight: 1.1 }}>{a.titulo}</div>
              {top ? SUBS.map((s) => (
                <div key={s.t} style={{
                  display: "flex", alignItems: "center", gap: 8, marginTop: 6, marginLeft: -12, padding: "3px 12px", borderRadius: 999,
                  fontFamily: F.body, fontSize: 24, fontWeight: 700, color: s.on > 0.5 ? "#fff" : C.ink2,
                  background: s.on > 0.5 ? C.accent : "transparent", width: "fit-content",
                }}>
                  <Icon name={s.t.startsWith("Franquicia") ? "store" : "users"} size={22} color={s.on > 0.5 ? "#fff" : C.muted} />{s.t}
                </div>
              )) : null}
            </div>
          </div>
        );
      })}

      <div style={{ position: "absolute", left: 120, right: 120, top: 890, textAlign: "center", fontFamily: F.body, fontSize: 30, color: C.ink2, opacity: nota }}>
        Responde, califica y agenda; lo que necesita una persona lo pasa <b style={{ color: C.ink }}>con la ficha completa.</b>
      </div>

      <Paquete k={ENTRADAS[0]} t0={v(M.wa + 0.3)} t1={v(M.wa + 1.0)} icon="wa" />
      <Paquete k={ENTRADAS[1]} t0={v(M.linea + 0.2)} t1={v(M.linea + 0.9)} icon="phone" />
      <Paquete k={ENTRADAS[2]} t0={v(M.sitio + 0.2)} t1={v(M.sitio + 0.9)} icon="web" />
      <Paquete k={SALIDAS[1]} t0={v(M.deriva + 0.3)} t1={v(M.deriva + 1.0)} icon="wa" />
      <Paquete k={SALIDAS[3]} t0={v(M.deriva + 0.6)} t1={v(M.deriva + 1.3)} icon="phone" />
      <Paquete k={SALIDAS[0]} t0={v(M.ventas + 0.1)} t1={v(M.ventas + 0.8)} icon="wa" />
      <Paquete k={SALIDAS[0]} t0={v(M.ventas + 0.4)} t1={v(M.ventas + 1.1)} icon="phone" />
      <Paquete k={SALIDAS[0]} t0={v(M.ventas + 0.7)} t1={v(M.ventas + 1.4)} icon="web" />

      <Pie seccion="4 / 4" />
    </AbsoluteFill>
  );
};

// Momentos de a6b: "Y en el panel," 0,1 · "ven todo lo que pasa:" 1,07 · "quién tomó cada consulta," 2,48 · "y cuánto tardó." 4,0
const MP = { panel: 0.1, todo: 1.07, quien: 2.48, tardo: 4.0 };
const NAR = "#c2410c";
const NAR_SOFT = "#fff4ed";

// Números del ejemplo del PDF (página 4): ilustrativos
const KPIS = [
  { n: 310, fmt: (x: number) => String(Math.round(x)), t: "consultas por WhatsApp, línea y web" },
  { n: 52, fmt: (x: number) => `${Math.round(x)} %`, t: "llegaron con la casa central cerrada" },
  { n: 6, fmt: (x: number) => `${Math.max(1, Math.round(x))} s`, t: "hasta la primera respuesta" },
];
// Por asesor (mediana), del mismo ejemplo; `alerta`: lo que la dirección mira (más de 20 min para tomarla)
const FILAS = [
  { quien: "Central 1", fichas: 34, tomo: "12 min", pend: 1 },
  { quien: "Central 2", fichas: 29, tomo: "25 min", pend: 4, alerta: true },
  { quien: "Showroom", fichas: 31, tomo: "9 min", pend: 0 },
  { quien: "Carlos Paz", fichas: 12, tomo: "40 min", pend: 2, alerta: true },
  { quien: "Franquicias", fichas: 15, tomo: "1 h 10", pend: 3, alerta: true },
];
const COLS = "1.6fr 1fr 1.2fr 1.4fr";

/** 4b. El panel: pocas cifras y quién tomó cada consulta y cuánto tardó (ejemplo con datos ilustrativos). */
export const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a6b + s;
  const panel = useIn(v(MP.panel), 0.7);
  const k = interpolate(t, [v(MP.todo), v(MP.todo + 1.2)], [0, 1], { ...CLAMP, easing: EASE });
  const filas = FILAS.map((_, i) => useIn(v(MP.quien + i * 0.12), 0.45));
  const tardo = interpolate(t, [v(MP.tardo), v(MP.tardo + 0.4)], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="El panel" text="Ven cada consulta:" accent="quién la tomó y cuánto tardó." size={62} />

      <div style={{
        position: "absolute", left: 120, top: 262, width: 1680, height: 700, borderRadius: 24, overflow: "hidden", border: `2px solid ${C.line2}`,
        background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.14)", opacity: panel, transform: `translateY(${(1 - panel) * 60}px)`,
      }}>
        <div style={{ background: C.ink, color: C.ctaInk, fontFamily: F.mono, fontSize: 21, letterSpacing: "0.05em", padding: "16px 30px", display: "flex", justifyContent: "space-between" }}>
          <span>PANEL · SQL AMOBLAMIENTOS</span>
          <span style={{ color: C.accentOnDark }}>EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA</span>
        </div>
        <div style={{ background: C.bg2, padding: 30, height: "100%", boxSizing: "border-box", display: "flex", gap: 30 }}>
          <div style={{ width: 470, display: "flex", flexDirection: "column", gap: 20 }}>
            {KPIS.map((x) => (
              <div key={x.t} style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "18px 26px", height: 172, boxSizing: "border-box" }}>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 74, color: C.accent, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>{x.fmt(x.n * k)}</div>
                <div style={{ fontFamily: F.body, fontSize: 26, color: C.ink2, marginTop: 6 }}>{x.t}</div>
              </div>
            ))}
          </div>
          <div style={{ flex: 1, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "22px 34px", height: 556, boxSizing: "border-box" }}>
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted }}>QUIÉN TOMÓ CADA CONSULTA DERIVADA</div>
            <div style={{ display: "grid", gridTemplateColumns: COLS, marginTop: 16, paddingBottom: 10, borderBottom: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.muted }}>
              <span>Quién</span><span style={{ textAlign: "right" }}>Fichas</span>
              <span style={{ textAlign: "right", color: tardo > 0.5 ? C.accent : C.muted }}>La tomó en</span>
              <span style={{ textAlign: "right" }}>Presup. +7 días</span>
            </div>
            {FILAS.map((r, i) => {
              const a = r.alerta ? tardo : 0;
              return (
                <div key={r.quien} style={{
                  display: "grid", gridTemplateColumns: COLS, alignItems: "center", height: 72, borderBottom: `2px solid ${C.line}`,
                  fontFamily: F.body, fontSize: 32, color: C.ink, opacity: filas[i], transform: `translateY(${(1 - filas[i]) * 16}px)`,
                  background: a > 0.5 ? NAR_SOFT : "transparent", margin: "0 -16px", padding: "0 16px",
                }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 14, fontWeight: 700 }}>
                    <Icon name="users" size={28} color={C.accent} />{r.quien}
                  </span>
                  <span style={{ textAlign: "right", fontFamily: F.mono, fontSize: 28 }}>{r.fichas}</span>
                  <span style={{ textAlign: "right", fontFamily: F.mono, fontSize: 28, color: a > 0.5 ? NAR : C.ink, fontWeight: 700 }}>{r.tomo}</span>
                  <span style={{ textAlign: "right", fontFamily: F.mono, fontSize: 28, color: a > 0.5 && r.pend > 0 ? NAR : C.ink }}>{r.pend}</span>
                </div>
              );
            })}
            <div style={{ fontFamily: F.body, fontSize: 21, color: C.muted, marginTop: 14, opacity: filas[4] }}>
              Mediana por asesor o local. Cada conversación se abre con su transcripción, su resumen y su resultado.
            </div>
          </div>
        </div>
      </div>

      <Pie seccion="4 / 4" fuente="Ejemplo con datos ilustrativos: muestra qué se mide, no un resultado." />
    </AbsoluteFill>
  );
};

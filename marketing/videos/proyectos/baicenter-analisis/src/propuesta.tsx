import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/baicenter-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Link, useIn, usePop } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// La propuesta en dos escenas, como goldman-analisis v3: el asesor de guardia (diagrama del PDF, página 3) y el panel
// (página 4). Momentos de a6a (s desde que arranca la voz), por las pausas de la toma:
// "Un asesor de guardia," 0,1 · "en sus mismos números." 1,45 · "Responde en segundos," 3,1 · "califica," 4,2 ·
// "llama en menos de un minuto," 5,2 · "agenda el test drive," 6,95 · "y le pasa la ficha al vendedor." 8,45–10,1
const M = { numeros: 1.45, responde: 3.1, califica: 4.2, llama: 5.2, agenda: 6.95, ficha: 8.45 };

type IconoCanal = "phone" | "wa";
const CANALES: { icon: IconoCanal; titulo: string; cy: number }[] = [
  { icon: "wa", titulo: "WhatsApp 1", cy: 330 },
  { icon: "wa", titulo: "WhatsApp 2", cy: 430 },
  { icon: "phone", titulo: "Teléfono fijo", cy: 530 },
];
// Su equipo, por marca (diagrama del PDF, página 3)
const EQUIPO = [
  { titulo: "BAIC y Arcfox", cy: 338 },
  { titulo: "Mitsubishi", cy: 428 },
  { titulo: "Foton y flotas", cy: 518 },
  { titulo: "Posventa y taller", cy: 608 },
];
const PASOS = [
  { n: 1, t: "Responde en segundos", at: M.responde },
  { n: 2, t: "Califica", at: M.califica },
  { n: 3, t: "Llama en menos de un minuto", at: M.llama },
  { n: 4, t: "Agenda el test drive", at: M.agenda },
  { n: 5, t: "Pasa la ficha al vendedor", at: M.ficha },
];

type P = { x: number; y: number };
const bez = (a: P, c: P, b: P, k: number): P => ({
  x: (1 - k) * (1 - k) * a.x + 2 * (1 - k) * k * c.x + k * k * b.x,
  y: (1 - k) * (1 - k) * a.y + 2 * (1 - k) * k * c.y + k * k * b.y,
});
type Curva = { a: P; b: P; c: P; d: string };
const curva = (a: P, b: P, c: P = { x: (a.x + b.x) / 2, y: a.y }): Curva => ({ a, b, c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` });
const AG = { x: 1010, y: 430 };
const EQ_X = 1400;
const ENTRADAS = CANALES.map((c) => curva({ x: 700, y: c.cy }, { x: AG.x - 100, y: AG.y }));
const SALIDAS = EQUIPO.map((e) => curva({ x: AG.x + 100, y: AG.y }, { x: EQ_X, y: e.cy }));
const VUELTA = curva({ x: AG.x - 100, y: 500 }, { x: 225, y: 512 }, { x: 560, y: 690 });

const Paquete: React.FC<{ k: Curva; t0: number; t1: number; children: React.ReactNode; bg?: string; w?: number }> = ({ k, t0, t1, children, bg = C.accent, w = 52 }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const u = interpolate(t, [t0, t1], [0, 1], { ...CLAMP, easing: EASE });
  const o = interpolate(t, [t0 - 0.1, t0, t1, t1 + 0.25], [0, 1, 1, 0], CLAMP);
  const p = bez(k.a, k.c, k.b, u);
  return (
    <div style={{
      position: "absolute", left: p.x - w / 2, top: p.y - 26, width: w, height: 52, borderRadius: 26, opacity: o,
      background: bg, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 22px rgba(36,86,230,.35)",
    }}>
      {children}
    </div>
  );
};

/** 4a. La propuesta: el asesor de guardia en sus mismos números, paso por paso. */
export const Propuesta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a6a + s;
  const clientes = useIn(v(0.1), 0.5);
  const agente = usePop(v(0.2));
  const canales = CANALES.map((_, i) => useIn(v(M.numeros + i * 0.15), 0.5));
  const equipo = EQUIPO.map((_, i) => useIn(v(0.6 + i * 0.1), 0.5));
  const pasos = PASOS.map((p) => interpolate(t, [v(p.at - 0.1), v(p.at + 0.3)], [0, 1], { ...CLAMP, easing: EASE }));
  const pasosIn = useIn(v(M.responde - 0.6), 0.5);
  const vuelta = interpolate(t, [v(M.llama), v(M.llama + 0.4)], [0, 1], CLAMP);
  const agenda = usePop(v(M.agenda + 0.2));
  const ficha = useIn(v(M.ficha + 0.9), 0.6);
  const baic = interpolate(t, [v(M.ficha + 0.8), v(M.ficha + 1.1)], [0, 1], CLAMP);
  const env = envs.a6a;
  const i = frame - Math.round(v(0) * fps);
  const talk = i >= 0 && i < env.length ? env[i] * 0.6 : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="La propuesta" text="Un asesor de guardia," accent="en sus mismos números." />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRADAS.map((e, n) => <Link key={n} d={e.d} color={C.accent} opacity={canales[n] * 0.5} />)}
        {SALIDAS.map((e, n) => <Link key={n} d={e.d} color={C.accent} opacity={equipo[n] * (n === 0 ? 0.45 + 0.45 * baic : 0.45)} width={n === 0 ? 5 + 3 * baic : 5} />)}
        <path d={VUELTA.d} stroke={C.accent} strokeWidth={4} strokeDasharray="10 10" fill="none" opacity={vuelta * 0.8} />
      </svg>

      {/* Sus clientes */}
      <div style={{
        position: "absolute", left: 120, top: 350, width: 210, height: 160, boxSizing: "border-box", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: 6, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 20, boxShadow: shadowCard,
        opacity: clientes,
      }}>
        <Icon name="users" size={46} color={C.ink2} />
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 27, color: C.ink }}>Sus clientes</div>
        <div style={{ fontFamily: F.body, fontSize: 18, color: C.muted, textAlign: "center", lineHeight: 1.2 }}>particulares y empresas</div>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {CANALES.map((c, n) => <path key={n} d={`M330 430 C 365 430, 365 ${c.cy}, 400 ${c.cy}`} stroke={C.line2} strokeWidth={3} fill="none" opacity={canales[n]} />)}
      </svg>
      <div style={{ position: "absolute", left: 340, top: 612, width: 460, textAlign: "center", fontFamily: F.mono, fontSize: 19, color: C.accent, opacity: vuelta }}>
        lo llama en menos de un minuto
      </div>

      {CANALES.map((c, n) => (
        <div key={c.titulo} style={{
          position: "absolute", left: 400, top: c.cy - 40, width: 300, height: 80, boxSizing: "border-box", padding: "0 20px",
          display: "flex", alignItems: "center", gap: 14, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, boxShadow: shadowCard,
          opacity: canales[n], transform: `translateX(${(1 - canales[n]) * -30}px)`,
        }}>
          <div style={{ width: 48, height: 48, borderRadius: 24, background: c.icon === "wa" ? C.okSoft : C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name={c.icon} size={26} color={c.icon === "wa" ? C.wa : C.accent} />
          </div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink, whiteSpace: "nowrap" }}>{c.titulo}</div>
        </div>
      ))}

      <div style={{ position: "absolute", left: AG.x - 100, top: AG.y - 100, width: 200, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente})` }}>
        <AgenteLogo size={200} talk={talk} style={{ filter: "drop-shadow(0 16px 30px rgba(36,86,230,.22))" }} />
        <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 20, whiteSpace: "nowrap" }}>
          Asesor de guardia · 24/7
        </div>
      </div>
      <div style={{
        position: "absolute", left: AG.x - 150, width: 300, top: 600, display: "flex", justifyContent: "center",
        transform: `scale(${agenda})`, opacity: Math.min(1, agenda * 1.5),
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, borderRadius: 14, padding: "10px 18px", background: C.accentSoft, border: `2px solid ${C.accent}` }}>
          <Icon name="calendar" size={26} color={C.accent} />
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, whiteSpace: "nowrap" }}>Test drive · sábado 10 h</span>
        </div>
      </div>

      <div style={{ position: "absolute", left: EQ_X, top: 270, fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted, opacity: equipo[0] }}>
        SU EQUIPO
      </div>
      {EQUIPO.map((e, n) => {
        const on = n === 0 ? baic : 0;
        return (
          <div key={e.titulo} style={{
            position: "absolute", left: EQ_X, top: e.cy - 38, width: 400, height: 76, boxSizing: "border-box", padding: "0 22px",
            display: "flex", alignItems: "center", gap: 14, borderRadius: 18, background: on > 0.5 ? C.accentSoft : "#fff",
            border: `2px solid ${on > 0.5 ? C.accent : C.line}`,
            boxShadow: on > 0.05 ? `0 0 0 ${8 * on}px rgba(36,86,230,.12), ${shadowCard}` : shadowCard,
            opacity: equipo[n], transform: `translateX(${(1 - equipo[n]) * 30}px) scale(${1 + 0.04 * on})`, transformOrigin: "left center",
          }}>
            <Icon name="users" size={28} color={C.accent} />
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: on > 0.5 ? C.accent : C.ink, whiteSpace: "nowrap" }}>{e.titulo}</div>
          </div>
        );
      })}

      {/* Los cinco pasos, que se encienden con la locución */}
      <div style={{ position: "absolute", left: 120, right: 120, top: 690, display: "flex", gap: 16, opacity: pasosIn }}>
        {PASOS.map((p, n) => {
          const on = pasos[n];
          return (
            <div key={p.n} style={{
              flex: 1, height: 104, boxSizing: "border-box", padding: "14px 20px", borderRadius: 18, display: "flex", alignItems: "center", gap: 14,
              background: on > 0.5 ? C.accent : "#fff", border: `2px solid ${on > 0.5 ? C.accent : C.line}`, boxShadow: shadowCard,
              transform: `scale(${1 + 0.03 * on})`,
            }}>
              <div style={{
                width: 42, height: 42, flex: "none", borderRadius: 21, display: "flex", alignItems: "center", justifyContent: "center",
                background: on > 0.5 ? "#fff" : C.accentSoft, color: C.accent, fontFamily: F.display, fontWeight: 800, fontSize: 24,
              }}>{p.n}</div>
              <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 25, lineHeight: 1.2, color: on > 0.5 ? "#fff" : C.ink2 }}>{p.t}</div>
            </div>
          );
        })}
      </div>

      {/* La ficha que recibe el vendedor (ejemplo del PDF, página 3) */}
      <div style={{
        position: "absolute", left: 120, right: 120, top: 832, height: 92, boxSizing: "border-box", display: "flex", alignItems: "center", gap: 24,
        padding: "0 28px", borderRadius: 18, border: `2px solid ${C.accent}`, background: "#fff", opacity: ficha, transform: `translateY(${(1 - ficha) * 20}px)`,
      }}>
        <span style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.06em", color: C.accent, whiteSpace: "nowrap" }}>FICHA DE EJEMPLO</span>
        <span style={{ fontFamily: F.mono, fontSize: 22, color: C.ink, whiteSpace: "nowrap" }}>
          <b style={{ color: C.accent }}>Caliente</b> · BJ30 híbrida · financiación bancaria · permuta Gol 2015, 120.000 km · test drive sábado 10 h
        </span>
      </div>

      {ENTRADAS.map((e, n) => (
        <Paquete key={n} k={e} t0={v(M.responde + n * 0.2)} t1={v(M.responde + 0.7 + n * 0.2)} bg={CANALES[n].icon === "wa" ? C.wa : C.accent}>
          <Icon name={CANALES[n].icon} size={26} color="#fff" />
        </Paquete>
      ))}
      <Paquete k={VUELTA} t0={v(M.llama + 0.1)} t1={v(M.llama + 1.3)}><Icon name="phone" size={26} color="#fff" /></Paquete>
      <Paquete k={SALIDAS[0]} t0={v(M.ficha + 0.1)} t1={v(M.ficha + 0.8)} bg={C.ink} w={92}>
        <span style={{ fontFamily: F.mono, fontSize: 18, color: "#fff" }}>ficha</span>
      </Paquete>

      <Pie seccion="4 / 4" fuente="El test drive y la ficha son un ejemplo." />
    </AbsoluteFill>
  );
};

// Momentos de a6b: "Lo que no se mide," 0,1 · "no se mejora." 1,2 · "En el panel ven cada consulta," 2,45 ·
// "cuánto tardó," 4,3 · "y quién la tomó." 5,4
const MP = { panel: 0.1, consulta: 2.45, tardo: 4.3, quien: 5.4 };

// Números del ejemplo del PDF (página 4): ilustrativos
const KPIS = [
  { n: 540, fmt: (x: number) => String(Math.round(x)), t: "consultas en los dos WhatsApp y el fijo", tardo: false },
  { n: 5, fmt: (x: number) => `${Math.max(1, Math.round(x))} s`, t: "hasta la primera respuesta (mediana)", tardo: true },
  { n: 41, fmt: (x: number) => `${Math.round(x)} %`, t: "llegaron con el showroom cerrado", tardo: false },
  { n: 48, fmt: (x: number) => `${Math.round(x)} s`, t: "hasta la llamada al interesado (mediana)", tardo: true },
  { n: 63, fmt: (x: number) => String(Math.round(x)), t: "test drives y 38 turnos de taller agendados", tardo: false },
];
const MARCAS = [["BAIC", 262], ["Arcfox", 94], ["Foton", 104], ["Mitsubishi", 80]] as const;
const TIPOS = [["0 km", 188], ["Financiación", 132], ["Posventa", 88], ["Permuta", 61], ["Repuestos", 42], ["Flotas", 29]] as const;
const FILAS = [
  { quien: "BAIC 1", fichas: 71, calientes: 18, tomo: "7 min", sin: 0 },
  { quien: "BAIC 2", fichas: 64, calientes: 15, tomo: "22 min", sin: 4, foco: true },
  { quien: "Arcfox", fichas: 38, calientes: 11, tomo: "9 min", sin: 1 },
  { quien: "Mitsubishi", fichas: 33, calientes: 7, tomo: "14 min", sin: 2 },
  { quien: "Foton", fichas: 19, calientes: 6, tomo: "11 min", sin: 0 },
];
const COLS = "1.5fr 0.9fr 1.1fr 1.2fr 1.1fr";

const Barras: React.FC<{ titulo: string; datos: readonly (readonly [string, number])[]; max: number; k: number }> = ({ titulo, datos, max, k }) => (
  <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "20px 24px", boxSizing: "border-box", height: "100%" }}>
    <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: C.muted }}>{titulo}</div>
    <div style={{ marginTop: 14 }}>
      {datos.map(([n, x]) => (
        <div key={n} style={{ display: "grid", gridTemplateColumns: "150px 1fr 56px", alignItems: "center", gap: 10, height: 44 }}>
          <span style={{ fontFamily: F.body, fontSize: 21, color: C.ink2, whiteSpace: "nowrap" }}>{n}</span>
          <div style={{ height: 14, width: `${(x / max) * 100 * k}%`, borderRadius: 7, background: C.accent }} />
          <span style={{ fontFamily: F.mono, fontSize: 20, color: C.ink, textAlign: "right" }}>{Math.round(x * k)}</span>
        </div>
      ))}
    </div>
  </div>
);

/** 4b. El panel: lo que no se mide no se mejora (ejemplo con datos ilustrativos). */
export const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a6b + s;
  const panel = useIn(v(MP.panel), 0.7);
  const k = interpolate(t, [v(MP.panel + 0.6), v(MP.panel + 1.8)], [0, 1], { ...CLAMP, easing: EASE });
  const consulta = interpolate(t, [v(MP.consulta), v(MP.consulta + 0.3)], [0, 1], CLAMP);
  const tardo = interpolate(t, [v(MP.tardo), v(MP.tardo + 0.3)], [0, 1], CLAMP);
  const quien = interpolate(t, [v(MP.quien), v(MP.quien + 0.3)], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Mejora continua, con números" text="Lo que no se mide no se mejora." accent="El panel lo mide cada día." size={58} />

      <div style={{
        position: "absolute", left: 120, top: 250, width: 1680, height: 726, borderRadius: 24, overflow: "hidden", border: `2px solid ${C.line2}`,
        background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.14)", opacity: panel, transform: `translateY(${(1 - panel) * 60}px)`,
      }}>
        <div style={{ background: C.ink, color: C.ctaInk, fontFamily: F.mono, fontSize: 20, letterSpacing: "0.05em", padding: "14px 30px", display: "flex", justifyContent: "space-between" }}>
          <span>PANEL · BAIC CENTER / GRUPO SIGNATURE</span>
          <span style={{ color: C.accentOnDark }}>EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA</span>
        </div>
        <div style={{ background: C.bg2, padding: 24, height: 670, boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", gap: 18 }}>
            {KPIS.map((x, n) => {
              const on = x.tardo ? tardo : n === 0 ? consulta * (1 - tardo) : 0;
              return (
                <div key={x.t} style={{
                  flex: 1, background: on > 0.5 ? C.accentSoft : "#fff", border: `2px solid ${on > 0.5 ? C.accent : C.line}`, borderRadius: 16,
                  padding: "14px 20px", height: 150, boxSizing: "border-box",
                }}>
                  <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 56, color: C.accent, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>{x.fmt(x.n * k)}</div>
                  <div style={{ fontFamily: F.body, fontSize: 20, lineHeight: 1.25, color: C.ink2, marginTop: 6 }}>{x.t}</div>
                </div>
              );
            })}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1.6fr", gap: 18, height: 452 }}>
            <Barras titulo="POR MARCA" datos={MARCAS} max={262} k={k} />
            <Barras titulo="POR TIPO DE CONSULTA" datos={TIPOS} max={188} k={k} />
            <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "20px 26px", boxSizing: "border-box" }}>
              <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: C.muted }}>POR VENDEDOR (MEDIANA)</div>
              <div style={{ display: "grid", gridTemplateColumns: COLS, marginTop: 14, paddingBottom: 10, borderBottom: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 700, fontSize: 19, color: C.muted }}>
                <span style={{ color: quien > 0.5 ? C.accent : C.muted }}>Quién</span><span style={{ textAlign: "right" }}>Fichas</span>
                <span style={{ textAlign: "right" }}>Calientes</span>
                <span style={{ textAlign: "right", color: tardo > 0.5 ? C.accent : C.muted }}>La tomó en</span>
                <span style={{ textAlign: "right" }}>Sin tomar</span>
              </div>
              {FILAS.map((r) => {
                const a = r.foco ? quien : 0;
                return (
                  <div key={r.quien} style={{
                    display: "grid", gridTemplateColumns: COLS, alignItems: "center", height: 62, borderBottom: `2px solid ${C.line}`,
                    fontFamily: F.mono, fontSize: 23, color: C.ink, opacity: k, background: a > 0.5 ? C.accentSoft : "transparent", margin: "0 -12px", padding: "0 12px",
                  }}>
                    <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 23 }}>{r.quien}</span>
                    <span style={{ textAlign: "right" }}>{r.fichas}</span>
                    <span style={{ textAlign: "right" }}>{r.calientes}</span>
                    <span style={{ textAlign: "right", color: tardo > 0.5 ? C.accent : C.ink, fontWeight: tardo > 0.5 ? 700 : 500 }}>{r.tomo}</span>
                    <span style={{ textAlign: "right" }}>{r.sin}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <Pie seccion="4 / 4" fuente="Ejemplo con datos ilustrativos: muestra qué se mide, no un resultado." />
    </AbsoluteFill>
  );
};

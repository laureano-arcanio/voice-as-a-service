import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/experto-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Link, useIn, usePop } from "../../../src/comun/ui";
import { NAR, NAR_SOFT, Pie } from "./escenas";
import { AT } from "./timeline";

// La propuesta (PDF, página 3) en dos escenas: canales → agente → tipos de consulta → su equipo por área, con el
// énfasis en las cotizaciones al asesor de cada sucursal; después el panel simple.

// Momentos de a5 (s desde que arranca la voz), por las pausas de la toma:
// "Proponemos un agente" 0,1 · "que atiende su WhatsApp," 1,5 · "el cero ochocientos" 2,35 · "y la web," 3,5 ·
// "a toda hora." 4,0 · "Responde las preguntas frecuentes," 4,96 · "pasa los reclamos a posventa," 6,7 ·
// "y cada cotización, completa," 8,25 · "al asesor de su sucursal." 9,8–11,1
const M = { wa: 1.5, cero800: 2.35, web: 3.5, frecuentes: 4.96, reclamos: 6.7, cotizacion: 8.25, asesor: 9.8 };

type IconoCanal = "phone" | "wa" | "web";
const CANALES: { icon: IconoCanal; titulo: string; y: number; at: number }[] = [
  { icon: "wa", titulo: "WhatsApp", y: 330, at: M.wa },
  { icon: "phone", titulo: "0800 y teléfonos", y: 446, at: M.cero800 },
  { icon: "web", titulo: "Su web", y: 562, at: M.web },
];
// Tipos de consulta y áreas: diagrama del PDF, página 3
const TIPOS = [
  { t: "Preguntas frecuentes", at: M.frecuentes },
  { t: "Reclamo", at: M.reclamos },
  { t: "Cotización", at: M.cotizacion },
];
const SUCURSALES = ["Punilla", "Carlos Paz", "Zona Sur", "Rivadavia"];
const AREAS = [
  { titulo: "Ventas · cotizaciones", sub: "El asesor de cada sucursal", y: 300, h: 180 },
  { titulo: "Posventa · reclamos", sub: "", y: 502, h: 86 },
  { titulo: "Logística · retiros y envíos", sub: "", y: 608, h: 86 },
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
const AG = { x: 900, y: 470 };
const AREA_X = 1290;
const ENTRADAS = CANALES.map((c) => curva({ x: 500, y: c.y + 46 }, { x: AG.x - 100, y: AG.y }));
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

/** 3a. La propuesta: un agente en sus canales que responde lo general y pasa cada consulta a su área (sobre todo, cotizaciones). */
export const Propuesta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a5 + s;
  const agente = usePop(v(0.1));
  const canales = CANALES.map((c) => useIn(v(c.at), 0.5));
  const tipos = TIPOS.map((x) => usePop(v(x.at + 0.1)));
  const resuelto = useIn(v(M.frecuentes + 0.9), 0.4);
  const areas = AREAS.map((_, i) => useIn(v(M.reclamos - 0.3 + i * 0.12), 0.5));
  const suc = SUCURSALES.map((_, i) => useIn(v(M.asesor + 0.1 + i * 0.12), 0.35));
  const nota = useIn(v(M.asesor + 0.9), 0.6);
  const ventas = interpolate(t, [v(M.cotizacion + 0.3), v(M.cotizacion + 0.8)], [0, 1], { ...CLAMP, easing: EASE });
  const env = envs.a5;
  const i = frame - Math.round(v(0) * fps);
  const talk = i >= 0 && i < env.length ? env[i] * 0.6 : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="La solución propuesta" text="Un agente con IA," accent="en todos sus canales." out={v(M.frecuentes)} />
      <Headline eyebrow="La solución propuesta" text="Resuelve lo general y pasa cada consulta" accent="a su área." at={v(M.frecuentes + 0.2)} size={60} />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRADAS.map((e, n) => <Link key={n} d={e.d} color={C.accent} opacity={canales[n] * 0.5} />)}
        {SALIDAS.map((e, n) => (
          <Link key={n} d={e.d} color={C.accent} opacity={areas[n] * (n === 0 ? 0.5 + 0.4 * ventas : 0.5 - 0.25 * ventas)} width={n === 0 ? 5 + 3 * ventas : 5} />
        ))}
      </svg>

      {CANALES.map((c, n) => (
        <div key={c.titulo} style={{
          position: "absolute", left: 120, top: c.y, width: 380, height: 92, boxSizing: "border-box", padding: "0 24px",
          display: "flex", alignItems: "center", gap: 16, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 20, boxShadow: shadowCard,
          opacity: canales[n], transform: `translateX(${(1 - canales[n]) * -40}px)`,
        }}>
          <div style={{ width: 56, height: 56, borderRadius: 28, background: c.icon === "wa" ? C.okSoft : C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name={c.icon} size={30} color={c.icon === "wa" ? C.wa : C.accent} />
          </div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink, whiteSpace: "nowrap" }}>{c.titulo}</div>
        </div>
      ))}

      <div style={{ position: "absolute", left: AG.x - 100, top: AG.y - 100, width: 200, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente})` }}>
        <AgenteLogo size={200} talk={talk} style={{ filter: "drop-shadow(0 16px 30px rgba(36,86,230,.22))" }} />
        <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 20, whiteSpace: "nowrap" }}>
          Atentina · 24 horas
        </div>
      </div>

      {/* Tipos de consulta: cada uno entra con su frase; la cotización en el acento */}
      <div style={{ position: "absolute", left: AG.x - 330, width: 660, top: 690, display: "flex", justifyContent: "center", gap: 12 }}>
        {TIPOS.map((x, n) => {
          const on = n === 2;
          return (
            <div key={x.t} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <div style={{
                borderRadius: 999, padding: "10px 22px", fontFamily: F.body, fontWeight: 700, fontSize: 25, whiteSpace: "nowrap",
                background: on ? C.accent : C.accentSoft, color: on ? "#fff" : C.accent2,
                transform: `scale(${tipos[n] * (on ? 1 + 0.12 * ventas : 1)})`, opacity: Math.min(1, tipos[n] * 1.5),
              }}>{x.t}</div>
              {n === 0 ? (
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: F.mono, fontSize: 18, color: C.ok, opacity: resuelto }}>
                  <Icon name="check" size={20} color={C.ok} />la responde el agente
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* Su equipo, por área; Ventas toma el acento con "cada cotización, completa, al asesor de su sucursal" */}
      <div style={{ position: "absolute", left: AREA_X, top: 254, fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted, opacity: areas[0] }}>
        SU EQUIPO
      </div>
      {AREAS.map((a, n) => {
        const top = n === 0;
        const p = areas[n];
        const e = top ? ventas : 0;
        return (
          <div key={a.titulo} style={{
            position: "absolute", left: AREA_X, top: a.y, width: 510, height: a.h, boxSizing: "border-box", padding: top ? "20px 26px" : "0 26px",
            display: "flex", flexDirection: top ? "column" : "row", alignItems: top ? "flex-start" : "center", gap: top ? 0 : 16, borderRadius: 20,
            background: e > 0.5 ? C.accentSoft : "#fff",
            border: `${top ? 3 : 2}px solid ${e > 0.5 ? C.accent : C.line}`,
            boxShadow: e > 0.05 ? `0 0 0 ${8 * e}px rgba(36,86,230,.12), ${shadowCard}` : shadowCard,
            opacity: p * (top ? 1 : 1 - 0.35 * ventas), transform: `translateX(${(1 - p) * 40}px) scale(${1 + 0.04 * e})`, transformOrigin: "left center",
          }}>
            {top ? (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <Icon name="users" size={34} color={C.accent} />
                  <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: e > 0.5 ? C.accent : C.ink, lineHeight: 1.1, whiteSpace: "nowrap" }}>{a.titulo}</div>
                </div>
                <div style={{ fontFamily: F.body, fontSize: 22, color: C.ink2, marginTop: 6 }}>{a.sub}</div>
                <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                  {SUCURSALES.map((s, k) => (
                    <div key={s} style={{
                      borderRadius: 999, padding: "5px 12px", background: "#fff", border: `2px solid ${C.accent}`, fontFamily: F.body, fontWeight: 700,
                      fontSize: 18, color: C.accent2, whiteSpace: "nowrap", opacity: suc[k], transform: `scale(${0.8 + 0.2 * suc[k]})`,
                    }}>{s}</div>
                  ))}
                </div>
              </>
            ) : (
              <>
                <Icon name="users" size={28} color={C.accent} />
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink, lineHeight: 1.1, whiteSpace: "nowrap" }}>{a.titulo}</div>
              </>
            )}
          </div>
        );
      })}

      <div style={{ position: "absolute", left: 120, right: 120, top: 890, textAlign: "center", fontFamily: F.body, fontSize: 30, color: C.ink2, opacity: nota }}>
        Resuelve lo general; lo demás lo pasa <b style={{ color: C.ink }}>con el resumen escrito.</b>
      </div>

      <Paquete k={ENTRADAS[0]} t0={v(M.wa + 0.3)} t1={v(M.wa + 1.0)} icon="wa" />
      <Paquete k={ENTRADAS[1]} t0={v(M.cero800 + 0.4)} t1={v(M.cero800 + 1.1)} icon="phone" />
      <Paquete k={ENTRADAS[2]} t0={v(M.web + 0.2)} t1={v(M.web + 0.9)} icon="web" />
      <Paquete k={SALIDAS[1]} t0={v(M.reclamos + 0.4)} t1={v(M.reclamos + 1.1)} icon="wa" />
      <Paquete k={SALIDAS[2]} t0={v(M.reclamos + 0.9)} t1={v(M.reclamos + 1.6)} icon="phone" />
      <Paquete k={SALIDAS[0]} t0={v(M.cotizacion + 0.5)} t1={v(M.cotizacion + 1.2)} icon="wa" />
      <Paquete k={SALIDAS[0]} t0={v(M.cotizacion + 0.9)} t1={v(M.cotizacion + 1.6)} icon="phone" />
      <Paquete k={SALIDAS[0]} t0={v(M.cotizacion + 1.3)} t1={v(M.cotizacion + 2.0)} icon="web" />

      <Pie seccion="3 / 4" />
    </AbsoluteFill>
  );
};

// Momentos de a6 (gonzalo): "Y en el panel," 0,1 · "ven quién tomó cada cotización," 0,8 · "y cuánto tardó." 2,35–3,1
const MP = { panel: 0.0, quien: 0.8, tardo: 2.35 };

// Números del ejemplo del PDF (página 4): ilustrativos
const KPIS = [
  { n: 1180, fmt: (x: number) => Math.round(x).toLocaleString("es-AR"), t: "consultas en todos los canales" },
  { n: 5, fmt: (x: number) => `${Math.max(1, Math.round(x))} s`, t: "hasta la primera respuesta" },
  { n: 236, fmt: (x: number) => String(Math.round(x)), t: "cotizaciones completas a un asesor" },
];
// Cotizaciones por asesor (mediana), del mismo ejemplo; `alerta`: lo que el dueño mira
const FILAS = [
  { quien: "Asesor Carlos Paz", recibio: 82, tomo: "7 min", sin: 0 },
  { quien: "Asesor Rivadavia", recibio: 64, tomo: "22 min", sin: 4, alerta: true },
  { quien: "Asesor Punilla", recibio: 51, tomo: "12 min", sin: 1 },
  { quien: "Asesor Zona Sur", recibio: 39, tomo: "9 min", sin: 2 },
];
const COLS = "1.9fr 1fr 1.2fr 1fr";

/** 4. El panel: pocas cifras y quién tomó cada cotización y cuánto tardó (ejemplo con datos ilustrativos). */
export const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a6 + s;
  const panel = useIn(v(MP.panel), 0.6);
  const k = interpolate(t, [v(0.3), v(1.5)], [0, 1], { ...CLAMP, easing: EASE });
  const filas = FILAS.map((_, i) => useIn(v(MP.quien + i * 0.15), 0.45));
  const tardo = interpolate(t, [v(MP.tardo), v(MP.tardo + 0.4)], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="El panel" text="Ven cada cotización:" accent="quién la tomó y cuánto tardó." size={62} />

      <div style={{
        position: "absolute", left: 120, top: 262, width: 1680, height: 700, borderRadius: 24, overflow: "hidden", border: `2px solid ${C.line2}`,
        background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.14)", opacity: panel, transform: `translateY(${(1 - panel) * 60}px)`,
      }}>
        <div style={{ background: C.ink, color: C.ctaInk, fontFamily: F.mono, fontSize: 21, letterSpacing: "0.05em", padding: "16px 30px", display: "flex", justifyContent: "space-between" }}>
          <span>PANEL · EXPERTO</span>
          <span style={{ color: "#ffd2b8" }}>EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA</span>
        </div>
        <div style={{ background: C.bg2, padding: 30, height: "100%", boxSizing: "border-box", display: "flex", gap: 30 }}>
          <div style={{ width: 470, display: "flex", flexDirection: "column", gap: 20 }}>
            {KPIS.map((x) => (
              <div key={x.t} style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "18px 26px", height: 172, boxSizing: "border-box" }}>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 74, color: C.accent, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>{x.fmt(x.n * k)}</div>
                <div style={{ fontFamily: F.body, fontSize: 25, color: C.ink2, marginTop: 6 }}>{x.t}</div>
              </div>
            ))}
          </div>
          <div style={{ flex: 1, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "24px 34px", height: 556, boxSizing: "border-box" }}>
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted }}>COTIZACIONES POR ASESOR</div>
            <div style={{ display: "grid", gridTemplateColumns: COLS, marginTop: 22, paddingBottom: 12, borderBottom: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.muted }}>
              <span>Quién</span><span style={{ textAlign: "right" }}>Recibió</span>
              <span style={{ textAlign: "right", color: tardo > 0.5 ? C.accent : C.muted }}>La tomó en</span>
              <span style={{ textAlign: "right" }}>Sin tomar</span>
            </div>
            {FILAS.map((r, i) => {
              const a = r.alerta ? tardo : 0;
              return (
                <div key={r.quien} style={{
                  display: "grid", gridTemplateColumns: COLS, alignItems: "center", height: 92, borderBottom: `2px solid ${C.line}`,
                  fontFamily: F.body, fontSize: 32, color: C.ink, opacity: filas[i], transform: `translateY(${(1 - filas[i]) * 16}px)`,
                  background: a > 0.5 ? NAR_SOFT : "transparent", margin: "0 -16px", padding: "0 16px",
                }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 14, fontWeight: 700, whiteSpace: "nowrap" }}>
                    <Icon name="users" size={28} color={C.accent} />{r.quien}
                  </span>
                  <span style={{ textAlign: "right", fontFamily: F.mono, fontSize: 30 }}>{r.recibio}</span>
                  <span style={{ textAlign: "right", fontFamily: F.mono, fontSize: 30, color: a > 0.5 ? NAR : C.ink, fontWeight: 700 }}>{r.tomo}</span>
                  <span style={{ textAlign: "right", fontFamily: F.mono, fontSize: 30, color: a > 0.5 && r.sin > 0 ? NAR : C.ink }}>{r.sin}</span>
                </div>
              );
            })}
            <div style={{ fontFamily: F.body, fontSize: 22, color: C.muted, marginTop: 18, opacity: filas[3] }}>
              Mediana por asesor. Cada conversación se abre con lo que se dijo y cómo terminó.
            </div>
          </div>
        </div>
      </div>

      <Pie seccion="4 / 4" fuente="Ejemplo con datos ilustrativos: muestra qué se mide, no un resultado." />
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/sqlamoblamientos-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Link, useIn, usePop, Wave } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// v3: la propuesta del PDF v2 (página 3): atiende llamadas con voz (0800 o 0810 nuevo, la línea de casa central y las
// llamadas de WhatsApp) y mensajes, con sus pedidos y su catálogo al día, y pasa a una persona con la charla y la ficha.
// Momentos de a6a (s desde que arranca): "Atiende con voz," 0,12 · "en un cero ochocientos," 1,21 · "su línea y su
// WhatsApp." 2,74 · "Conoce sus productos," 4,38 · "y sabe cómo va cada pedido." 5,63–7,27
// a6c (s desde que arranca): "Y cuando hace falta," 0,12 · "pasa a una persona:" 1,48 · "al asesor," 2,8 ·
// "o a la franquicia de la zona," 3,5 · "con la charla y la ficha." 5,26–6,66
// v6 (paula): a6a "en un cero ochocientos," 1,39 · "su línea y su WhatsApp." 2,92 · "Conoce sus productos," 4,43 · "y sabe cómo
// va cada pedido." 5,5–7,45; a6c "pasa a una persona:" 1,31 · "al asesor," 2,7 · "o a la franquicia..." 3,38 · "con la charla..." 4,86–5,92
const M = { voz: 0.12, cero800: 1.39, linea: 2.95, wa: 3.76, sitio: 4.1, productos: 4.43, pedidos: 5.5 };
const P = { falta: 0.12, persona: 1.31, asesor: 2.7, franquicia: 3.4, ficha: 4.86 };

type IconoCanal = "phone" | "wa" | "web";
const CANALES: { icon: IconoCanal; titulo: string; sub: string; y: number; at: number }[] = [
  { icon: "phone", titulo: "0800 / 0810", sub: "nuevo, para todo el país", y: 280, at: M.cero800 },
  { icon: "phone", titulo: "Línea de la casa", sub: "casa central", y: 384, at: M.linea },
  { icon: "wa", titulo: "WhatsApp", sub: "mensajes, audios y llamadas", y: 488, at: M.wa },
  { icon: "web", titulo: "Su sitio web", sub: "llamar desde la página", y: 592, at: M.sitio },
];
// Una persona, a un paso (PDF v2, página 3): quién recibe el pase
const EQUIPO = [
  { t: "Asesores y locales", at: P.asesor, ventas: true },
  { t: "Franquicia de la zona", at: P.franquicia, ventas: true },
  { t: "Posventa", at: 99, ventas: false },
  { t: "Administración", at: 99, ventas: false },
  { t: "Producción", at: 99, ventas: false },
];

type Pt = { x: number; y: number };
const bez = (a: Pt, c: Pt, b: Pt, k: number): Pt => ({
  x: (1 - k) * (1 - k) * a.x + 2 * (1 - k) * k * c.x + k * k * b.x,
  y: (1 - k) * (1 - k) * a.y + 2 * (1 - k) * k * c.y + k * k * b.y,
});
type Curva = { a: Pt; b: Pt; c: Pt; d: string };
const curva = (a: Pt, b: Pt): Curva => {
  const c = { x: (a.x + b.x) / 2, y: a.y };
  return { a, b, c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` };
};
const AG = { x: 900, y: 420 };
const EQ = { x: 1290, y: 262, w: 510, h: 440 };
const ENTRADAS = CANALES.map((c) => curva({ x: 520, y: c.y + 44 }, { x: AG.x - 100, y: AG.y }));
const PASE = curva({ x: AG.x + 100, y: AG.y }, { x: EQ.x, y: 420 });
const COLOR: Record<IconoCanal, string> = { phone: C.accent, wa: C.wa, web: C.accent2 };

const Paquete: React.FC<{ k: Curva; t0: number; t1: number; bg: string; w?: number; children: React.ReactNode }> = ({ k, t0, t1, bg, w = 52, children }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const u = interpolate(t, [t0, t1], [0, 1], { ...CLAMP, easing: EASE });
  const o = interpolate(t, [t0 - 0.1, t0, t1, t1 + 0.25], [0, 1, 1, 0], CLAMP);
  const p = bez(k.a, k.c, k.b, u);
  return (
    <div style={{
      position: "absolute", left: p.x - w / 2, top: p.y - 26, width: w, height: 52, borderRadius: 26, opacity: o,
      background: bg, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, boxShadow: "0 8px 22px rgba(36,86,230,.35)",
    }}>
      {children}
    </div>
  );
};

/** 4a. La propuesta: el asesor de guardia atiende con voz y por mensaje, con sus datos, y pasa a una persona lo que hace falta. */
export const Propuesta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a6a + s;
  const w = (s: number) => AT.a6c + s;
  const agente = usePop(v(0.1));
  const voz = interpolate(t, [v(M.voz), v(M.voz + 0.3), v(M.cero800 + 1.6), v(M.cero800 + 2.0)], [0, 1, 1, 0], CLAMP);
  const canales = CANALES.map((c) => useIn(v(c.at), 0.5));
  const datos = useIn(v(M.productos - 0.2), 0.5);
  const catalogo = interpolate(t, [v(M.productos), v(M.productos + 0.3)], [0, 1], CLAMP);
  const pedidos = interpolate(t, [v(M.pedidos), v(M.pedidos + 0.3)], [0, 1], CLAMP);
  const datosLink = Math.max(catalogo, pedidos) * (1 - interpolate(t, [w(0), w(0.4)], [0, 0.6], CLAMP));
  const equipo = useIn(w(P.falta), 0.6);
  const pase = interpolate(t, [w(P.persona), w(P.persona + 0.4)], [0, 1], { ...CLAMP, easing: EASE });
  const marcas = EQUIPO.map((e) => interpolate(t, [w(e.at), w(e.at + 0.3)], [0, 1], CLAMP));
  const nota = useIn(w(P.ficha + 0.2), 0.6);
  const envA = envs.a6a;
  const envC = envs.a6c;
  const ia = frame - Math.round(v(0) * fps);
  const ic = frame - Math.round(w(0) * fps);
  const talk = (ia >= 0 && ia < envA.length ? envA[ia] : 0) * 0.6 + (ic >= 0 && ic < envC.length ? envC[ic] : 0) * 0.6;
  return (
    <AbsoluteFill>
      <Headline eyebrow="La propuesta" text="Un asesor de guardia," accent="y una persona cuando hace falta." size={56} />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRADAS.map((e, n) => <Link key={n} d={e.d} color={C.accent} opacity={canales[n] * 0.45} />)}
        <path d={`M${AG.x} ${AG.y + 150} L${AG.x} ${AG.y + 238}`} stroke={C.accent} strokeWidth={4} strokeDasharray="8 8" opacity={datos * (0.35 + 0.55 * datosLink)} />
        <Link d={PASE.d} color={C.accent} opacity={equipo * (0.35 + 0.6 * pase)} width={5 + 5 * pase} />
      </svg>

      {CANALES.map((c, n) => (
        <div key={c.titulo} style={{
          position: "absolute", left: 120, top: c.y, width: 400, height: 88, boxSizing: "border-box", padding: "0 20px",
          display: "flex", alignItems: "center", gap: 14, background: "#fff", border: `2px solid ${n === 0 ? C.accent : C.line}`, borderRadius: 20, boxShadow: shadowCard,
          opacity: canales[n], transform: `translateX(${(1 - canales[n]) * -40}px)`,
        }}>
          <div style={{ width: 52, height: 52, flex: "none", borderRadius: 26, background: c.icon === "wa" ? C.okSoft : C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name={c.icon} size={28} color={c.icon === "wa" ? C.wa : C.accent} />
          </div>
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 29, color: C.ink, whiteSpace: "nowrap", lineHeight: 1.1 }}>{c.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 19, color: C.muted, whiteSpace: "nowrap", marginTop: 2 }}>{c.sub}</div>
          </div>
        </div>
      ))}

      {/* El asesor de guardia: atiende con voz (onda mientras dice "Atiende con voz") */}
      <div style={{ position: "absolute", left: AG.x - 100, top: AG.y - 100, width: 200, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente})` }}>
        <AgenteLogo size={200} talk={talk} style={{ filter: "drop-shadow(0 16px 30px rgba(36,86,230,.22))" }} />
        <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 20, whiteSpace: "nowrap" }}>
          Asesor de guardia · 24/7
        </div>
      </div>
      <div style={{
        position: "absolute", left: AG.x - 230, top: AG.y - 168, width: 460, display: "flex", justifyContent: "center", opacity: voz,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, borderRadius: 999, padding: "8px 18px", background: C.accent }}>
          <Icon name="phone" size={22} color="#fff" />
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 21, color: "#fff", whiteSpace: "nowrap" }}>Atiende con voz</span>
          <Wave n={5} h={22} color="#fff" />
        </div>
      </div>

      {/* Sus datos: pedidos y catálogo */}
      <div style={{
        position: "absolute", left: AG.x - 240, top: AG.y + 238, width: 480, boxSizing: "border-box", padding: "16px 22px", borderRadius: 20,
        background: "#fff", border: `2px solid ${datosLink > 0.5 ? C.accent : C.line}`, boxShadow: shadowCard, opacity: datos, transform: `translateY(${(1 - datos) * 20}px)`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.06em", color: C.muted, whiteSpace: "nowrap" }}>SUS DATOS · DE SU SISTEMA O PLANILLA</div>
        <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
          {[{ t: "Catálogo", k: catalogo, i: "store" as const }, { t: "Pedidos", k: pedidos, i: "calendar" as const }].map((x) => (
            <div key={x.t} style={{
              flex: 1, display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderRadius: 14,
              background: x.k > 0.5 ? C.accent : C.accentSoft, transform: `scale(${1 + 0.04 * x.k})`,
            }}>
              <Icon name={x.i} size={24} color={x.k > 0.5 ? "#fff" : C.accent} />
              <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 23, color: x.k > 0.5 ? "#fff" : C.accent2 }}>{x.t}</span>
            </div>
          ))}
        </div>
        <div style={{ fontFamily: F.body, fontSize: 19, color: C.ink2, marginTop: 10 }}>Productos, tiempos y la etapa de cada pedido, al día.</div>
      </div>

      {/* Una persona, a un paso: el énfasis de la escena */}
      <div style={{
        position: "absolute", left: EQ.x, top: EQ.y, width: EQ.w, height: EQ.h, boxSizing: "border-box", padding: "24px 28px", borderRadius: 24,
        background: pase > 0.5 ? C.accentSoft : "#fff", border: `${pase > 0.5 ? 3 : 2}px solid ${pase > 0.5 ? C.accent : C.line}`,
        boxShadow: pase > 0.05 ? `0 0 0 ${10 * pase}px rgba(36,86,230,.12), ${shadowCard}` : shadowCard,
        opacity: equipo, transform: `translateX(${(1 - equipo) * 40}px)`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>SU EQUIPO</div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 8 }}>
          <Icon name="users" size={40} color={C.accent} />
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 35, color: pase > 0.5 ? C.accent : C.ink, lineHeight: 1.05, whiteSpace: "nowrap" }}>Una persona, a un paso</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 20 }}>
          {EQUIPO.map((e, n) => {
            const on = marcas[n];
            return (
              <div key={e.t} style={{
                display: "flex", alignItems: "center", gap: 12, height: 54, boxSizing: "border-box", padding: "0 18px", borderRadius: 14,
                background: on > 0.5 ? C.accent : "#fff", border: `2px solid ${on > 0.5 ? C.accent : C.line}`,
                transform: `scale(${1 + 0.03 * on})`, transformOrigin: "left center",
              }}>
                <Icon name={e.t.startsWith("Franquicia") ? "store" : "users"} size={24} color={on > 0.5 ? "#fff" : C.accent} />
                <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: e.ventas ? 25 : 23, color: on > 0.5 ? "#fff" : C.ink }}>{e.t}</span>
                {e.ventas ? <span style={{ marginLeft: "auto", fontFamily: F.mono, fontSize: 15, color: on > 0.5 ? "#dbe6ff" : C.muted }}>VENTAS</span> : null}
              </div>
            );
          })}
        </div>
      </div>
      <div style={{
        position: "absolute", left: AG.x + 100, width: EQ.x - AG.x - 100, top: 316, textAlign: "center", fontFamily: F.mono, fontSize: 18, whiteSpace: "nowrap",
        lineHeight: 1.35, color: C.accent, opacity: pase,
      }}>
        pasa a una persona<br />con la charla y la ficha
      </div>

      <div style={{
        position: "absolute", left: 120, right: 120, top: 880, height: 84, boxSizing: "border-box", display: "flex", alignItems: "center", justifyContent: "center",
        gap: 14, borderRadius: 18, background: C.ink, opacity: nota, transform: `translateY(${(1 - nota) * 20}px)`,
      }}>
        <Icon name="check" size={32} color={C.accentOnDark} />
        <span style={{ fontFamily: F.body, fontSize: 30, color: C.ctaInk }}>
          Resuelve lo que puede; lo demás lo atiende su equipo, <b style={{ color: C.accentOnDark }}>sin que el cliente repita nada.</b>
        </span>
      </div>

      <Paquete k={ENTRADAS[0]} t0={v(M.cero800 + 0.3)} t1={v(M.cero800 + 1.0)} bg={COLOR.phone}><Icon name="phone" size={26} color="#fff" /></Paquete>
      <Paquete k={ENTRADAS[1]} t0={v(M.linea + 0.2)} t1={v(M.linea + 0.9)} bg={COLOR.phone}><Icon name="phone" size={26} color="#fff" /></Paquete>
      <Paquete k={ENTRADAS[2]} t0={v(M.wa + 0.2)} t1={v(M.wa + 0.9)} bg={COLOR.wa}><Icon name="wa" size={26} color="#fff" /></Paquete>
      <Paquete k={ENTRADAS[3]} t0={v(M.sitio + 0.2)} t1={v(M.sitio + 0.9)} bg={COLOR.web}><Icon name="web" size={26} color="#fff" /></Paquete>
      <Paquete k={PASE} t0={w(P.persona + 0.1)} t1={w(P.persona + 1.0)} bg={C.accent}><Icon name="phone" size={26} color="#fff" /></Paquete>
      <Paquete k={PASE} t0={w(P.ficha)} t1={w(P.ficha + 0.9)} bg={C.ink} w={180}>
        <span style={{ fontFamily: F.mono, fontSize: 18, color: "#fff", whiteSpace: "nowrap" }}>charla + ficha</span>
      </Paquete>

      <Pie seccion="4 / 4" />
    </AbsoluteFill>
  );
};

// Momentos de a6b (v3): "Y en el panel," 0,1 · "ven qué pasó a una persona," 0,98 · "quién la tomó," 2,62 · "y cuánto tardó." 3,43
const MP = { panel: 0.1, todo: 0.86, quien: 2.53, tardo: 3.33 }; // v6 (paula)
const NAR = "#c2410c";
const NAR_SOFT = "#fff4ed";

// Números del ejemplo del PDF (página 4): ilustrativos
const KPIS = [
  { t: "consultas: llamadas, WhatsApp y web", fmt: (k: number) => String(Math.round(310 * k)) },
  { t: "resueltas solas · pasadas a una persona", fmt: (k: number) => `${Math.round(189 * k)} · ${Math.round(121 * k)}` },
];
// Por canal (PDF v2, página 4), con el 0800 y las llamadas de WhatsApp
const CANAL = [["WhatsApp chat", 151], ["0800 / 0810", 72], ["Línea", 41], ["Sitio web", 28], ["Llamada WA", 18]] as const;
// Pasadas a una persona (mediana), del mismo ejemplo; `alerta`: lo que la dirección mira (más de 20 min para tomarla)
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
  const pasadas = interpolate(t, [v(MP.todo), v(MP.todo + 0.3)], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="El panel" text="Qué pasó a una persona:" accent="quién la tomó y cuánto tardó." size={62} />

      <div style={{
        position: "absolute", left: 120, top: 262, width: 1680, height: 700, borderRadius: 24, overflow: "hidden", border: `2px solid ${C.line2}`,
        background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.14)", opacity: panel, transform: `translateY(${(1 - panel) * 60}px)`,
      }}>
        <div style={{ background: C.ink, color: C.ctaInk, fontFamily: F.mono, fontSize: 21, letterSpacing: "0.05em", padding: "16px 30px", display: "flex", justifyContent: "space-between" }}>
          <span>PANEL · SQL AMOBLAMIENTOS</span>
          <span style={{ color: C.accentOnDark }}>EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA</span>
        </div>
        <div style={{ background: C.bg2, padding: 30, height: "100%", boxSizing: "border-box", display: "flex", gap: 30 }}>
          <div style={{ width: 500, display: "flex", flexDirection: "column", gap: 16 }}>
            {KPIS.map((x, n) => {
              const on = n === 1 ? pasadas : 0;
              return (
                <div key={x.t} style={{
                  background: on > 0.5 ? C.accentSoft : "#fff", border: `2px solid ${on > 0.5 ? C.accent : C.line}`, borderRadius: 18,
                  padding: "14px 24px", height: 138, boxSizing: "border-box",
                }}>
                  <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 62, color: C.accent, lineHeight: 1.05, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>{x.fmt(k)}</div>
                  <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink2, marginTop: 4, whiteSpace: "nowrap" }}>{x.t}</div>
                </div>
              );
            })}
            <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "14px 24px", height: 274, boxSizing: "border-box" }}>
              <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: C.muted }}>POR CANAL</div>
              {CANAL.map(([n, x]) => (
                <div key={n} style={{ display: "grid", gridTemplateColumns: "150px 1fr 48px", alignItems: "center", gap: 10, height: 44 }}>
                  <span style={{ fontFamily: F.body, fontSize: 21, color: C.ink2, whiteSpace: "nowrap" }}>{n}</span>
                  <div style={{ height: 13, width: `${(x / 151) * 100 * k}%`, borderRadius: 7, background: C.accent }} />
                  <span style={{ fontFamily: F.mono, fontSize: 20, color: C.ink, textAlign: "right" }}>{Math.round(x * k)}</span>
                </div>
              ))}
            </div>
          </div>
          <div style={{ flex: 1, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 18, padding: "22px 34px", height: 556, boxSizing: "border-box" }}>
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.muted }}>PASADAS A UNA PERSONA: QUIÉN Y CUÁNTO TARDÓ</div>
            <div style={{ display: "grid", gridTemplateColumns: COLS, marginTop: 16, paddingBottom: 10, borderBottom: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.muted }}>
              <span>Quién</span><span style={{ textAlign: "right" }}>Pases</span>
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

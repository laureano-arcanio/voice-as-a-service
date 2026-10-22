import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/goldman-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Link, useIn, usePop } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// Momentos de a6 (s desde que arranca la voz), por las pausas de la toma
const M = { cero800: 2.7, wa: 3.6, web: 4.2, deriva: 4.9, panel: 6.4, resenas: 7.3, cadaDia: 9.7 };

const CANALES = [
  { icon: "phone" as const, titulo: "Línea 0800 / 0810", y: 262, at: M.cero800 },
  { icon: "wa" as const, titulo: "WhatsApp", y: 374, at: M.wa },
  { icon: "web" as const, titulo: "Chat en su web", y: 486, at: M.web },
];
const EQUIPO = ["Vendedores", "Instalaciones", "Service y posventa", "Empresas y obras"];

// Números del ejemplo del PDF (página 4): ilustrativos
const KPIS = [
  { n: 812, fmt: (v: number) => String(Math.round(v)), t: "consultas en los tres canales" },
  { n: 4, fmt: (v: number) => `${Math.max(1, Math.round(v))} s`, t: "hasta la primera respuesta (mediana)" },
  { n: 37, fmt: (v: number) => `${Math.round(v)} %`, t: "llegaron con el local cerrado" },
  { n: 61, fmt: (v: number) => `${Math.round(v)} %`, t: "resueltas por el agente; el resto, derivadas" },
  { n: 143, fmt: (v: number) => String(Math.round(v)), t: "presupuestos · 58 turnos · 41 reclamos con caso" },
];
const CANAL = [
  { icon: "wa" as const, label: "WhatsApp", n: 498 },
  { icon: "phone" as const, label: "Línea 0800", n: 236 },
  { icon: "web" as const, label: "Chat web", n: 78 },
];

type P = { x: number; y: number };
const bez = (a: P, c: P, b: P, k: number): P => ({
  x: (1 - k) * (1 - k) * a.x + 2 * (1 - k) * k * c.x + k * k * b.x,
  y: (1 - k) * (1 - k) * a.y + 2 * (1 - k) * k * c.y + k * k * b.y,
});
const curva = (a: P, b: P) => {
  const c = { x: (a.x + b.x) / 2, y: a.y };
  return { a, b, c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` };
};
const AG = { x: 960, y: 405 };
const ENTRADAS = CANALES.map((c) => curva({ x: 540, y: c.y + 46 }, { x: AG.x - 95, y: AG.y }));
const SALIDA = curva({ x: AG.x + 95, y: AG.y }, { x: 1380, y: AG.y });

const Paquete: React.FC<{ k: ReturnType<typeof curva>; t0: number; t1: number; icon: "phone" | "wa" }> = ({ k, t0, t1, icon }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const u = interpolate(t, [t0, t1], [0, 1], { ...CLAMP, easing: EASE });
  const o = interpolate(t, [t0 - 0.1, t0, t1, t1 + 0.25], [0, 1, 1, 0], CLAMP);
  const p = bez(k.a, k.c, k.b, u);
  return (
    <div style={{
      position: "absolute", left: p.x - 26, top: p.y - 26, width: 52, height: 52, borderRadius: 26, opacity: o,
      background: icon === "wa" ? C.wa : C.accent, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 22px rgba(36,86,230,.35)",
    }}>
      <Icon name={icon} size={26} color="#fff" />
    </div>
  );
};

/** 4. La propuesta: el especialista de guardia en los tres canales, que deriva, y el panel como centro. */
export const Propuesta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.a6 + s;
  const agente = usePop(v(0.2));
  const canales = CANALES.map((c) => useIn(v(c.at), 0.5));
  const equipo = useIn(v(M.deriva), 0.5);
  const panel = useIn(v(M.panel), 0.7);
  const k = interpolate(t, [v(M.panel + 0.3), v(M.panel + 1.6)], [0, 1], { ...CLAMP, easing: EASE });
  const pulso = interpolate(t, [v(M.cadaDia), v(M.cadaDia + 0.3), v(M.cadaDia + 0.9)], [0, 1, 0.4], CLAMP);
  const dim = 1 - 0.4 * panel;
  const env = envs.a6;
  const i = frame - Math.round(v(0) * fps);
  const talk = i >= 0 && i < env.length && t < v(M.panel) ? env[i] * 0.6 : 0;
  const maxCanal = Math.max(...CANAL.map((c) => c.n));
  return (
    <AbsoluteFill>
      <Headline eyebrow="La propuesta" text="El especialista de guardia," accent="en los tres canales." out={v(M.panel)} />
      <Headline eyebrow="El centro de la propuesta: ver la atención" text="Hoy se mide en reseñas." accent="Con el panel, cada día." at={v(M.panel + 0.25)} />

      <div style={{ position: "absolute", inset: 0, opacity: dim }}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          {ENTRADAS.map((e, n) => <Link key={n} d={e.d} color={C.accent} opacity={canales[n] * 0.5} />)}
          <Link d={SALIDA.d} color={C.accent} opacity={equipo * 0.6} />
        </svg>
        {CANALES.map((c, n) => (
          <div key={c.titulo} style={{
            position: "absolute", left: 120, top: c.y, width: 420, height: 92, boxSizing: "border-box", padding: "0 24px",
            display: "flex", alignItems: "center", gap: 16, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 20, boxShadow: shadowCard,
            opacity: canales[n], transform: `translateX(${(1 - canales[n]) * -40}px)`,
          }}>
            <div style={{ width: 56, height: 56, borderRadius: 28, background: c.icon === "wa" ? C.okSoft : C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon name={c.icon} size={30} color={c.icon === "wa" ? C.wa : C.accent} />
            </div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>{c.titulo}</div>
          </div>
        ))}

        <div style={{ position: "absolute", left: AG.x - 95, top: AG.y - 95, width: 190, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente})` }}>
          <AgenteLogo size={190} talk={talk} style={{ filter: "drop-shadow(0 16px 30px rgba(36,86,230,.22))" }} />
          <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 20, whiteSpace: "nowrap" }}>
            Especialista de guardia · 24/7
          </div>
        </div>

        <div style={{
          position: "absolute", left: 1380, top: 262, width: 420, height: 316, boxSizing: "border-box", padding: "22px 28px",
          background: "#fff", border: `2px solid ${C.line}`, borderRadius: 22, boxShadow: shadowCard, opacity: equipo, transform: `translateX(${(1 - equipo) * 40}px)`,
        }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Su equipo</div>
          {EQUIPO.map((x) => (
            <div key={x} style={{ display: "flex", alignItems: "center", gap: 12, fontFamily: F.body, fontWeight: 600, fontSize: 24, color: C.ink2, marginTop: 12 }}>
              <Icon name="users" size={24} color={C.accent} />{x}
            </div>
          ))}
          <div style={{ fontFamily: F.mono, fontSize: 18, color: C.muted, marginTop: 14 }}>con la ficha completa</div>
        </div>

        <Paquete k={ENTRADAS[0]} t0={v(M.deriva - 0.7)} t1={v(M.deriva)} icon="phone" />
        <Paquete k={SALIDA} t0={v(M.deriva + 0.1)} t1={v(M.deriva + 0.9)} icon="phone" />
      </div>

      {/* El panel (maqueta con los números ilustrativos del PDF) */}
      <div style={{
        position: "absolute", left: 120, top: 660, width: 1680, height: 296, borderRadius: 24, overflow: "hidden", border: `2px solid ${C.line2}`,
        background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.14)", opacity: panel, transform: `translateY(${(1 - panel) * 60}px)`,
      }}>
        <div style={{ background: C.ink, color: C.ctaInk, fontFamily: F.mono, fontSize: 19, letterSpacing: "0.05em", padding: "12px 26px", display: "flex", justifyContent: "space-between" }}>
          <span>PANEL · ISAÍAS GOLDMAN SA</span>
          <span style={{ color: C.ctaMuted }}>EJEMPLO CON DATOS ILUSTRATIVOS · UNA SEMANA DE NOVIEMBRE</span>
        </div>
        <div style={{ background: C.bg2, padding: "20px 24px", height: "100%", boxSizing: "border-box" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16 }}>
            {KPIS.map((x) => (
              <div key={x.t} style={{
                background: "#fff", border: `2px solid ${pulso > 0.5 ? C.accent : C.line}`, borderRadius: 16, padding: "14px 18px", height: 138, boxSizing: "border-box",
                boxShadow: pulso > 0.05 ? `0 0 0 ${6 * pulso}px rgba(36,86,230,.14)` : "none",
              }}>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 52, color: C.accent, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>{x.fmt(x.n * k)}</div>
                <div style={{ fontFamily: F.body, fontSize: 20, lineHeight: 1.25, color: C.ink2, marginTop: 6 }}>{x.t}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 30, marginTop: 20, alignItems: "center" }}>
            <span style={{ fontFamily: F.mono, fontSize: 17, color: C.muted, letterSpacing: "0.06em" }}>POR CANAL</span>
            {CANAL.map((c) => (
              <div key={c.label} style={{ flex: 1, display: "flex", alignItems: "center", gap: 10, fontFamily: F.body, fontSize: 20, color: C.ink2 }}>
                <Icon name={c.icon} size={22} color={c.icon === "wa" ? C.wa : C.accent} />
                <span style={{ whiteSpace: "nowrap" }}>{c.label}</span>
                <div style={{ flex: 1, height: 12, borderRadius: 6, background: C.surface2 }}>
                  <div style={{ height: 12, borderRadius: 6, width: `${(c.n / maxCanal) * 100 * k}%`, background: c.icon === "wa" ? C.wa : C.accent }} />
                </div>
                <span style={{ fontFamily: F.mono, fontSize: 18 }}>{Math.round(c.n * k)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Pie seccion="4 / 4" />
    </AbsoluteFill>
  );
};

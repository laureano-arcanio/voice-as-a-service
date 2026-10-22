import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { Headline, Icon, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

// Todos los números del panel son ilustrativos (README, "Afirmaciones")
// Alineados con el ejemplo del PDF goldman-propuesta v1 (página 4): mismos números ilustrativos
const NAV = ["Inicio", "Conversaciones", "Agentes", "WhatsApp", "Contactos", "Equipo"];

const CANAL = [
  { icon: "wa" as const, label: "WhatsApp", n: 498 },
  { icon: "phone" as const, label: "Línea 0800", n: 236 },
  { icon: "web" as const, label: "Chat web", n: 78 },
];
const TIPO = [
  { label: "Ventas", n: 312 },
  { label: "Precios", n: 164 },
  { label: "Instalaciones", n: 121 },
  { label: "Posventa", n: 96 },
  { label: "Productos", n: 84 },
  { label: "Otros", n: 35 },
];
const VENDEDORES = [
  { who: "Vendedor 1", area: "Ventas", n: 74, toma: "6 min" },
  { who: "Vendedor 2", area: "Ventas", n: 61, toma: "18 min" },
  { who: "Instalaciones", area: "Turnos", n: 52, toma: "11 min" },
  { who: "Posventa", area: "Reclamos", n: 47, toma: "25 min" },
  { who: "Empresas", area: "Obras", n: 23, toma: "9 min" },
];
// Consultas por hora (0 a 23) y horas con el local cerrado (lunes a viernes de 8:30 a 13 y de 14:30 a 18:30)
const HORAS = [12, 8, 5, 3, 3, 5, 10, 22, 36, 50, 56, 60, 54, 44, 40, 50, 54, 52, 46, 48, 46, 40, 30, 20];
const CERRADA = (h: number) => h < 8 || h === 13 || h >= 19;
const TOTAL_H = HORAS.reduce((a, b) => a + b, 0);
const FUERA = Math.round((HORAS.filter((_, h) => CERRADA(h)).reduce((a, b) => a + b, 0) / TOTAL_H) * 100);

const KPIS = [
  { label: "Consultas", fmt: (k: number) => String(Math.round(812 * k)), foco: "" },
  { label: "Primera respuesta", fmt: (k: number) => `${Math.max(1, Math.round(4 * k))} s`, foco: "tiempos" },
  { label: "Fuera de horario", fmt: (k: number) => `${Math.round(FUERA * k)} %`, foco: "fuera" },
  { label: "Resueltas por el agente", fmt: (k: number) => `${Math.round(61 * k)} %`, foco: "derivaciones" },
];

// Momentos de g4 (s desde que arranca la voz), por las pausas de la toma
const M = { canal: 1.5, tipo: 2.4, tiempos: 3.8, fuera: 4.8, derivaciones: 5.9 };
type Foco = "" | keyof typeof M;

/** Tarjeta del panel que se resalta cuando la locución la nombra. */
const Bloque: React.FC<{ foco: Foco; activo: Foco; style: React.CSSProperties; titulo?: string; children: React.ReactNode }> = ({
  foco, activo, style, titulo, children,
}) => {
  const on = activo !== "" && activo === foco;
  const dim = activo !== "" && !on;
  return (
    <div style={{
      position: "absolute", background: "#fff", borderRadius: 18, boxSizing: "border-box", padding: "16px 20px",
      border: `2px solid ${on ? C.accent : C.line}`, boxShadow: on ? "0 0 0 6px rgba(36,86,230,.14), 0 16px 40px rgba(11,18,32,.12)" : "none",
      opacity: dim ? 0.5 : 1, transform: `scale(${on ? 1.02 : 1})`, ...style,
    }}>
      {titulo ? <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 23, color: C.ink, marginBottom: 10 }}>{titulo}</div> : null}
      {children}
    </div>
  );
};

/** 3. El panel: todas las comunicaciones de los tres canales, con sus métricas. */
export const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.g4;
  const win = usePop(0.05);
  const k = interpolate(t, [0.1, 1.4], [0, 1], { ...CLAMP, easing: EASE });
  const activo: Foco = (Object.keys(M) as (keyof typeof M)[]).reduce<Foco>((a, id) => (t >= M[id] ? id : a), "");
  const maxCanal = Math.max(...CANAL.map((c) => c.n));
  const maxTipo = Math.max(...TIPO.map((c) => c.n));
  const maxHora = Math.max(...HORAS);
  return (
    <AbsoluteFill>
      <Headline eyebrow="El centro de la propuesta: ver la atención" text="Hoy se mide en reseñas." accent="Con el panel, cada día." />

      <div style={{ position: "absolute", left: 120, top: 228, width: 1680, height: 812, transform: `scale(${win})`, transformOrigin: "50% 100%" }}>
        <div style={{ position: "absolute", inset: 0, background: "#fff", borderRadius: 28, border: `2px solid ${C.line}`, boxShadow: "0 24px 60px rgba(11,18,32,.14)", overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 20px", background: C.surface2, borderBottom: `2px solid ${C.line}` }}>
            {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
            <div style={{ fontFamily: F.mono, fontSize: 19, color: C.muted, marginLeft: 14 }}>app.atentina.com.ar</div>
          </div>
          <div style={{ display: "flex", height: "100%" }}>
            <div style={{ width: 220, borderRight: `2px solid ${C.line}`, padding: "22px 14px", background: "#fbfcfe" }}>
              <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 140, marginLeft: 8, marginBottom: 20 }} />
              {NAV.map((n, i) => (
                <div key={n} style={{
                  fontFamily: F.body, fontSize: 20, fontWeight: i === 0 ? 700 : 500, color: i === 0 ? C.accent : C.ink2,
                  background: i === 0 ? C.accentSoft : "transparent", borderRadius: 10, padding: "9px 14px", marginBottom: 3,
                }}>
                  {n}
                </div>
              ))}
            </div>

            <div style={{ flex: 1, position: "relative" }}>
              {/* Título y filtros */}
              <div style={{ position: "absolute", left: 28, right: 28, top: 18, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 30, color: C.ink }}>Isaías Goldman SA</div>
                <div style={{ display: "flex", gap: 10 }}>
                  {["Una semana de noviembre", "Datos ilustrativos"].map((x) => (
                    <div key={x} style={{ border: `2px solid ${C.line}`, borderRadius: 999, padding: "6px 16px", fontFamily: F.body, fontSize: 18, color: C.ink2 }}>{x}</div>
                  ))}
                </div>
              </div>

              {/* KPIs */}
              {KPIS.map((x, i) => (
                <Bloque key={x.label} foco={x.foco as Foco} activo={activo}
                  style={{ left: 28 + i * 355, top: 74, width: 337, height: 110 }}>
                  <div style={{ fontFamily: F.body, fontSize: 19, color: C.muted }}>{x.label}</div>
                  <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, color: C.ink, fontVariantNumeric: "tabular-nums" }}>{x.fmt(k)}</div>
                </Bloque>
              ))}

              {/* Por canal */}
              <Bloque foco="canal" activo={activo} titulo="Por canal" style={{ left: 28, top: 204, width: 400, height: 276 }}>
                {CANAL.map((c) => (
                  <div key={c.label} style={{ marginBottom: 14 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: F.body, fontSize: 19, color: C.ink2 }}>
                      <Icon name={c.icon} size={22} color={c.icon === "wa" ? C.wa : C.accent} />
                      <span style={{ flex: 1 }}>{c.label}</span>
                      <span style={{ fontFamily: F.mono, fontSize: 18 }}>{Math.round(c.n * k)}</span>
                    </div>
                    <div style={{ height: 12, borderRadius: 6, background: C.surface2, marginTop: 6 }}>
                      <div style={{ height: 12, borderRadius: 6, width: `${(c.n / maxCanal) * 100 * k}%`, background: c.icon === "wa" ? C.wa : C.accent }} />
                    </div>
                  </div>
                ))}
              </Bloque>

              {/* Por tipo de consulta */}
              <Bloque foco="tipo" activo={activo} titulo="Por tipo de consulta" style={{ left: 446, top: 204, width: 450, height: 276 }}>
                {TIPO.map((c) => (
                  <div key={c.label} style={{ display: "grid", gridTemplateColumns: "140px 1fr 50px", alignItems: "center", gap: 10, marginBottom: 7, fontFamily: F.body, fontSize: 19, color: C.ink2 }}>
                    <span>{c.label}</span>
                    <div style={{ height: 14, borderRadius: 7, background: C.surface2 }}>
                      <div style={{ height: 14, borderRadius: 7, width: `${(c.n / maxTipo) * 100 * k}%`, background: C.accent }} />
                    </div>
                    <span style={{ fontFamily: F.mono, fontSize: 18, textAlign: "right" }}>{Math.round(c.n * k)}</span>
                  </div>
                ))}
              </Bloque>

              {/* Derivaciones por vendedor */}
              <Bloque foco="derivaciones" activo={activo} titulo="Derivaciones por persona" style={{ left: 914, top: 204, width: 490, height: 276 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 80px 90px", gap: 8, fontFamily: F.body, fontSize: 16, color: C.muted, paddingBottom: 6 }}>
                  <span>Persona</span><span>Área</span><span style={{ textAlign: "right" }}>Derivadas</span><span style={{ textAlign: "right" }}>La tomó en</span>
                </div>
                {VENDEDORES.map((r) => (
                  <div key={r.who} style={{ display: "grid", gridTemplateColumns: "1fr 100px 80px 90px", gap: 8, alignItems: "center", padding: "5px 0", borderTop: `1px solid ${C.line}`, fontFamily: F.body, fontSize: 19, color: C.ink2 }}>
                    <span style={{ fontWeight: 600, color: C.ink }}>{r.who}</span>
                    <span>{r.area}</span>
                    <span style={{ fontFamily: F.mono, fontSize: 18, textAlign: "right" }}>{Math.round(r.n * k)}</span>
                    <span style={{ fontFamily: F.mono, fontSize: 18, textAlign: "right" }}>{r.toma}</span>
                  </div>
                ))}
              </Bloque>

              {/* Consultas por hora */}
              <Bloque foco="fuera" activo={activo} titulo="Consultas por hora" style={{ left: 28, top: 500, width: 1376, height: 236 }}>
                <div style={{ position: "relative", height: 150, display: "flex", alignItems: "flex-end", gap: 10, paddingLeft: 4 }}>
                  {HORAS.map((n, h) => (
                    <div key={h} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4, height: "100%", justifyContent: "flex-end" }}>
                      <div style={{
                        width: "100%", height: (n / maxHora) * 118 * k, borderRadius: "6px 6px 0 0",
                        background: CERRADA(h) ? (activo === "fuera" ? C.warn : "#f2a39b") : C.accent,
                      }} />
                      <div style={{ fontFamily: F.mono, fontSize: 14, color: C.muted }}>{h}</div>
                    </div>
                  ))}
                </div>
                <div style={{ position: "absolute", right: 20, top: 16, display: "flex", gap: 20, fontFamily: F.body, fontSize: 17, color: C.ink2 }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 14, height: 14, borderRadius: 3, background: C.accent }} />Local abierto</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 14, height: 14, borderRadius: 3, background: C.warn }} />Local cerrado</span>
                </div>
              </Bloque>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

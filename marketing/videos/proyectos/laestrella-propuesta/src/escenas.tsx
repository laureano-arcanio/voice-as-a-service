import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Wave, useIn, usePop } from "../../../src/comun/ui";
import { Aro, Baldosa, Icon, Paquete, Pasajero, Pie, Rotulo, TelefonoIP, Traza, recta, useHabla, useT, type Curva } from "./piezas";
import { AT, CIERRE_LEN, en } from "./timeline";

const sube = (p: number, px = 26) => ({ opacity: p, transform: `translateY(${(1 - p) * px}px)` });
const card: React.CSSProperties = { position: "absolute", boxSizing: "border-box", background: "#fff", border: `2px solid ${C.line}`, borderRadius: 24, boxShadow: shadowCard };

// ---------- 1. Intro: quiénes son (PDF v2, hoja 1: las cuatro cifras y la línea de vanguardia) ----------

const CIFRAS = [
  { n: "+90", u: "años", t: "Uniendo Resistencia con el interior del Chaco, como empresa familiar.", at: en("a1", "más de noventa") },
  { n: "13", u: "corredores", t: "Que llegan a unas 60 localidades del interior chaqueño.", at: en("a1", "Trece") },
  { n: "6", u: "sucursales", t: "Y oficinas donde sus pasajeros compran y despachan.", at: en("a1", "seis sucursales") },
  { n: "3", u: "servicios más", t: "Encomiendas, alquiler de unidades y su tarjeta prepaga.", at: en("a1", "encomiendas") },
];

export const Intro: React.FC = () => {
  const logo = usePop(0.05);
  const titulo = useIn(0.2, 0.6);
  const ins = CIFRAS.map((c) => useIn(c.at - 0.1, 0.5));
  const banda = useIn(AT.a2 - 0.1, 0.5);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 64, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 260 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 168, textAlign: "center", fontFamily: F.mono, fontSize: 25, letterSpacing: "0.1em", color: C.accent, opacity: titulo }}>
        PROPUESTA · EMPRESA LA ESTRELLA · NOVIEMBRE 2026
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 218, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 76,
        lineHeight: 1.08, color: C.ink, letterSpacing: "-0.015em", ...sube(titulo, 20),
      }}>
        Todas las llamadas atendidas,<br /><span style={{ color: C.accent }}>y por primera vez, medidas.</span>
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 432, display: "flex", gap: 22 }}>
        {CIFRAS.map((c, i) => (
          <div key={c.u} style={{
            flex: 1, height: 310, boxSizing: "border-box", padding: "30px 32px", background: "#fff", border: `2px solid ${C.line}`, borderTop: `10px solid ${C.accent}`,
            borderRadius: 24, boxShadow: shadowCard, ...sube(ins[i], 30),
          }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 84, lineHeight: 1, color: C.ink, letterSpacing: "-0.02em" }}>{c.n}</div>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.accent, whiteSpace: "nowrap" }}>{c.u}</div>
            </div>
            <div style={{ fontFamily: F.body, fontSize: 29, lineHeight: 1.3, color: C.ink2, marginTop: 22 }}>{c.t}</div>
          </div>
        ))}
      </div>
      <div style={{
        position: "absolute", left: 120, right: 120, top: 784, height: 170, boxSizing: "border-box", padding: "0 56px", display: "flex", alignItems: "center", gap: 30,
        background: C.accentSoft, border: `2px solid ${C.accent}`, borderRadius: 24, ...sube(banda, 20),
      }}>
        <div style={{ width: 84, height: 84, flexShrink: 0, borderRadius: 22, background: "#fff", border: `2px solid ${C.accent}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg viewBox="0 0 24 24" width={50} height={50}><path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7Z" fill="none" stroke={C.accent} strokeWidth={2} strokeLinejoin="round" /></svg>
        </div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 46, lineHeight: 1.12, color: C.ink, letterSpacing: "-0.01em" }}>
          Un sistema como este los pone <span style={{ color: C.accent }}>a la vanguardia de la atención al pasajero en Argentina.</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 2. La propuesta: las 6 sucursales → el agente → lo resuelve, o pasa a la sucursal ----------

const SUC = [1, 2, 3, 4, 5, 6];
const SUC_Y = (i: number) => 340 + 38 + i * 88;
const AG = { x: 800, y: 600 };
const R = 100;
const ENTRAN: Curva[] = SUC.map((_, i) => ({ a: { x: 482, y: SUC_Y(i) }, c: { x: 600, y: SUC_Y(i) }, b: { x: AG.x - R - 10, y: AG.y } }));
const A_RESUELVE: Curva = { a: { x: AG.x + R + 10, y: AG.y - 20 }, c: { x: 960, y: 455 }, b: { x: 1040, y: 455 } };
const A_SUCURSAL: Curva = { a: { x: AG.x + R + 10, y: AG.y + 20 }, c: { x: 960, y: 762 }, b: { x: 1040, y: 762 } };
const RESUELVE = ["Horarios y paradas", "Disponibilidad", "Equipaje", "Encomiendas", "Alquiler y tarjeta"];

export const Propuesta: React.FC = () => {
  const t = useT();
  const llamadas = en("a3", "atiende todas");
  const sucs = SUC.map((_, i) => useIn(en("a3", "La propuesta") + 0.3 + i * 0.12, 0.4));
  const ag = usePop(en("a3", "un agente"));
  const rot = useIn(en("a3", "un agente") + 0.4, 0.5);
  const h24 = useIn(en("a3", "las veinticuatro"), 0.4);
  const cA = useIn(AT.a4 - 0.1, 0.5);
  const chips = RESUELVE.map((_, i) => useIn(AT.a4 + 0.3 + i * 0.18, 0.35));
  const noVende = usePop(en("a4", "No vende"));
  const cB = useIn(en("a4", "Y solo pasa"), 0.5);
  const motivo = useIn(en("a4", "con el motivo"), 0.5);
  const talk = useHabla("a3", AT.a3) + useHabla("a4", AT.a4);
  const salidaA = interpolate(t, [AT.a4, AT.a4 + 0.3], [0, 1], CLAMP);
  const salidaB = interpolate(t, [en("a4", "pasa a una"), en("a4", "pasa a una") + 0.3], [0, 1], CLAMP);
  return (
    <AbsoluteFill>
      <Headline eyebrow="La propuesta" text="Un solo agente para las seis sucursales," accent="las 24 horas." size={58} />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRAN.map((c, i) => <Traza key={i} curva={c} o={sucs[i] * interpolate(t, [llamadas, llamadas + 0.4], [0, 1], CLAMP)} />)}
        <Traza curva={A_RESUELVE} o={salidaA} />
        <Traza curva={A_SUCURSAL} o={salidaB} />
      </svg>

      <Rotulo style={{ position: "absolute", left: 120, top: 296, opacity: sucs[0] }}>Sus 6 sucursales</Rotulo>
      {SUC.map((n, i) => (
        <div key={n} style={{ ...card, left: 120, top: SUC_Y(i) - 38, width: 362, height: 76, borderRadius: 18, padding: "0 16px", display: "flex", alignItems: "center", gap: 16, opacity: sucs[i], transform: `translateX(${(1 - sucs[i]) * -24}px)` }}>
          <Baldosa size={48}><Icon name="phone" size={27} color="#fff" /></Baldosa>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 29, color: C.ink, whiteSpace: "nowrap" }}>Sucursal {n}</div>
        </div>
      ))}

      <div style={{ position: "absolute", left: AG.x - 230, width: 460, top: 432, display: "flex", justifyContent: "center", alignItems: "center", gap: 12, opacity: rot }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Agente de IA</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 14px", background: C.accentSoft, border: "2px solid #c9d6fb", borderRadius: 999, fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.accent2, opacity: 0.4 + 0.6 * h24, transform: `scale(${1 + 0.08 * h24 * (1 - h24) * 4})` }}>
          <Icon name="clock" size={22} color={C.accent} />24 horas
        </div>
      </div>
      <Aro t={t} cx={AG.x} cy={AG.y} r={R} on={rot} />
      <div style={{ position: "absolute", left: AG.x - 75, top: AG.y - 75, transform: `scale(${ag})` }}>
        <AgenteLogo size={150} talk={talk} />
      </div>
      <div style={{ position: "absolute", left: AG.x - 200, width: 400, top: AG.y + R + 26, textAlign: "center", fontFamily: F.body, fontSize: 24, color: C.ink2, opacity: rot }}>
        Con acento argentino
      </div>

      <div style={{ ...card, left: 1040, top: 290, width: 760, height: 330, padding: "24px 30px", border: `2px solid ${cA > 0.5 ? C.accent : C.line}`, ...sube(cA) }}>
        <Rotulo>Lo resuelve el agente</Rotulo>
        <div style={{ fontFamily: F.body, fontStyle: "italic", fontSize: 29, color: C.ink, marginTop: 12 }}>“¿A qué hora sale el domingo para Villa Ángela?”</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 16 }}>
          {RESUELVE.map((x, i) => (
            <div key={x} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 14, background: C.accentSoft, border: "2px solid #c9d6fb", fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.accent2, opacity: chips[i] }}>
              <Icon name="check" size={24} color={C.accent} />{x}
            </div>
          ))}
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 10, marginTop: 16, padding: "8px 18px", borderRadius: 14, background: C.warnSoft, border: "2px solid #f5c2bd", fontFamily: F.body, fontWeight: 800, fontSize: 25, color: C.warn, opacity: Math.min(1, noVende), transform: `scale(${0.8 + 0.2 * noVende})`, transformOrigin: "left center" }}>
          No vende: informa
        </div>
      </div>

      <div style={{ ...card, left: 1040, top: 650, width: 760, height: 230, padding: "22px 30px", border: `2px solid ${cB > 0.5 ? C.accent : C.line}`, ...sube(cB) }}>
        <Rotulo>Pasa a la sucursal, solo si hace falta</Rotulo>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 14 }}>
          <Baldosa size={56}><Icon name="store" size={32} color="#fff" /></Baldosa>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Una persona de la sucursal</div>
        </div>
        <div style={{ marginTop: 16, padding: "10px 18px", borderRadius: 14, background: C.bg2, border: `2px dashed ${C.line2}`, fontFamily: F.body, fontSize: 25, color: C.ink2, ...sube(motivo, 10) }}>
          <b style={{ color: C.accent }}>Motivo ya anotado:</b> comprar un pasaje para el domingo.
        </div>
      </div>

      {ENTRAN.map((c, i) => (
        <Paquete key={i} t={t} curva={c} a={llamadas + i * 0.16} b={llamadas + i * 0.16 + 0.9}><Wave n={4} h={20} /></Paquete>
      ))}
      <Paquete t={t} curva={A_RESUELVE} a={AT.a4 + 0.1} b={AT.a4 + 0.9}>Aa</Paquete>
      <Paquete t={t} curva={A_SUCURSAL} a={en("a4", "pasa a una")} b={en("a4", "con el motivo")}>motivo</Paquete>
      <Pie fuente="La consulta y el motivo son ejemplos." />
    </AbsoluteFill>
  );
};

// ---------- 3. Lo más importante: los datos de sus llamadas (PDF v2, hoja 1) ----------

const MIDE = [
  { t: "Cuántas entran", s: "Por día, por sucursal y por hora.", i: "phone" as const, at: en("a6", "cuántas entran") },
  { t: "Cuántas se pierden", s: "Las que nadie atendió.", i: "missed" as const, at: en("a6", "cuántas se pierden") },
  { t: "Quién atendió", s: "El agente o la persona de la sucursal.", i: "users" as const, at: en("a6", "quién atendió") },
  { t: "De qué hablan", s: "El motivo de cada llamada.", i: "ear" as const, at: en("a6", "de qué hablan") },
];
// Barras de ejemplo (ilustrativas, rotuladas): por sucursal y por hora del día
const POR_SUC = [0.92, 0.7, 0.55, 0.48, 0.36, 0.28];
const POR_HORA = [0.05, 0.03, 0.02, 0.02, 0.04, 0.12, 0.32, 0.55, 0.78, 0.86, 0.8, 0.7, 0.62, 0.58, 0.6, 0.66, 0.74, 0.88, 0.95, 0.8, 0.56, 0.34, 0.18, 0.09];

export const Datos: React.FC = () => {
  const izq = useIn(AT.a5 - 0.1, 0.5);
  const der = useIn(AT.a6 - 0.1, 0.5);
  const tiles = MIDE.map((m) => useIn(m.at - 0.1, 0.4));
  const pSuc = useIn(en("a6", "Por sucursal") - 0.1, 0.8);
  const pHora = useIn(en("a6", "por horario") - 0.1, 0.8);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo más importante" text="Sus llamadas, a la vista" accent="desde el primer día." />
      <div style={{ ...card, left: 120, top: 290, width: 520, height: 650, padding: "30px 34px", background: C.bg2, ...sube(izq) }}>
        <Rotulo color={C.muted}>Hoy · sin datos</Rotulo>
        <div style={{ marginTop: 26 }}><Baldosa size={72} gris><Icon name="missed" size={40} color="#fff" /></Baldosa></div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 42, lineHeight: 1.1, color: C.ink, marginTop: 24 }}>Ningún dato de sus llamadas.</div>
        <div style={{ fontFamily: F.body, fontSize: 27, lineHeight: 1.32, color: C.ink2, marginTop: 16 }}>
          No hay registro de cuántas entran a cada sucursal, ni de cuántas quedan sin atender.
        </div>
        <div style={{ display: "grid", gap: 14, marginTop: 30 }}>
          {[0.8, 0.6, 0.7].map((w, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: `${w * 100}%`, height: 18, borderRadius: 9, border: `2px dashed ${C.line2}` }} />
              <div style={{ fontFamily: F.mono, fontSize: 22, color: C.muted }}>?</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ ...card, left: 680, top: 290, width: 1120, height: 650, padding: "26px 32px", border: `2px solid ${C.accent}`, ...sube(der) }}>
        <Rotulo>Con Atentina · todo medido</Rotulo>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 18 }}>
          {MIDE.map((m, i) => (
            <div key={m.t} style={{ height: 132, boxSizing: "border-box", padding: "0 22px", display: "flex", alignItems: "center", gap: 18, borderRadius: 18, background: C.accentSoft, border: "2px solid #c9d6fb", ...sube(tiles[i], 14) }}>
              <Baldosa size={60}><Icon name={m.i} size={34} color="#fff" /></Baldosa>
              <div>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>{m.t}</div>
                <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink2, marginTop: 2 }}>{m.s}</div>
              </div>
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 18 }}>
          <div style={{ height: 250, boxSizing: "border-box", padding: "16px 22px", borderRadius: 18, border: `2px solid ${C.line}`, opacity: pSuc > 0 ? 1 : 0 }}>
            <Rotulo>Por sucursal</Rotulo>
            <div style={{ display: "grid", gap: 7, marginTop: 12 }}>
              {POR_SUC.map((w, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 34, fontFamily: F.mono, fontSize: 18, color: C.muted }}>S{i + 1}</div>
                  <div style={{ height: 20, width: `${w * 85 * pSuc}%`, borderRadius: 6, background: C.accent }} />
                </div>
              ))}
            </div>
          </div>
          <div style={{ height: 250, boxSizing: "border-box", padding: "16px 22px", borderRadius: 18, border: `2px solid ${C.line}`, opacity: pHora > 0 ? 1 : 0 }}>
            <Rotulo>Por horario</Rotulo>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 5, height: 150, marginTop: 14 }}>
              {POR_HORA.map((h, i) => <div key={i} style={{ flex: 1, height: 150 * h * pHora, borderRadius: 4, background: i >= 17 && i <= 19 ? C.accent2 : C.accent }} />)}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontFamily: F.mono, fontSize: 17, color: C.muted, marginTop: 6 }}>
              <span>0 h</span><span>12 h</span><span>23 h</span>
            </div>
          </div>
        </div>
      </div>
      <Pie fuente="Barras de ejemplo, ilustrativas." />
    </AbsoluteFill>
  );
};

// ---------- 4. Etapa 1: diagnóstico (PDF v2, hoja 2) ----------

const FY = 420;
const F1: Curva = recta({ x: 520, y: FY }, { x: 760, y: FY });
const F2: Curva = recta({ x: 1160, y: FY }, { x: 1400, y: FY });

const Nodo: React.FC<{ left: number; top: number; w: number; h: number; p: number; on?: boolean; icono: React.ReactNode; titulo: string; sub: string; rotulo?: string }> = ({ left, top, w, h, p, on, icono, titulo, sub, rotulo }) => (
  <div style={{ ...card, left, top, width: w, height: h, padding: "0 22px", display: "flex", alignItems: "center", gap: 16, border: `2px solid ${on ? C.accent : C.line}`, background: on ? C.accentSoft : "#fff", ...sube(p, 20) }}>
    {icono}
    <div>
      {rotulo ? <Rotulo style={{ fontSize: 18 }}>{rotulo}</Rotulo> : null}
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 31, lineHeight: 1.1, color: C.ink }}>{titulo}</div>
      <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink2, marginTop: 4 }}>{sub}</div>
    </div>
  </div>
);

export const Etapa1: React.FC = () => {
  const t = useT();
  const n1 = useIn(0.6, 0.45);
  const n2 = useIn(en("a7", "nuestro sistema") - 0.1, 0.45);
  const n3 = useIn(en("a7", "directo a la persona") - 0.1, 0.45);
  const sin = usePop(en("a7", "sin agente"));
  const igual = useIn(en("a7", "sin agente") + 0.6, 0.5);
  const base = useIn(en("a8", "medimos") - 0.1, 0.5);
  const aprende = useIn(en("a8", "aprendemos") - 0.1, 0.5);
  const e1 = useIn(0.1, 0.5);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Etapa 1 · en 10 días · de 1 a 2 semanas" text="Diagnóstico:" accent="medir antes de cambiar." />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Traza curva={F1} o={n2} />
        <Traza curva={F2} o={n3} />
      </svg>
      <div style={{ position: "absolute", right: 120, top: 92, display: "flex", alignItems: "center", gap: 12, padding: "12px 24px", borderRadius: 999, background: C.accent, color: "#fff", fontFamily: F.body, fontWeight: 800, fontSize: 30, opacity: e1 }}>
        <Icon name="calendar" size={32} color="#fff" />Arranca en 10 días
      </div>
      <Nodo left={120} top={FY - 75} w={400} h={150} p={n1} icono={<Baldosa size={64}><Pasajero size={38} /></Baldosa>} titulo="El pasajero" sub="llama como hoy" />
      <Nodo left={760} top={FY - 75} w={400} h={150} p={n2} on icono={<div style={{ width: 64, height: 64, flexShrink: 0, borderRadius: 18, background: "#fff", border: `2px solid ${C.line}`, display: "flex", alignItems: "center", justifyContent: "center" }}><Img src={staticFile("marca/atentina-mark.svg")} style={{ width: 42 }} /></div>} titulo="Nuestro sistema" sub="registra cada llamada" />
      <Nodo left={1400} top={FY - 75} w={400} h={150} p={n3} icono={<Baldosa size={64}><Icon name="store" size={36} color="#fff" /></Baldosa>} titulo="La sucursal" sub="atiende una persona" />
      <div style={{ position: "absolute", left: 1180, width: 200, top: FY - 70, display: "flex", justifyContent: "center", opacity: Math.min(1, sin), transform: `scale(${0.8 + 0.2 * sin})` }}>
        <div style={{ padding: "6px 14px", borderRadius: 999, background: "#fff", border: `2px solid ${C.line2}`, fontFamily: F.body, fontWeight: 800, fontSize: 22, color: C.ink2, whiteSpace: "nowrap" }}>sin agente</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: FY + 104, textAlign: "center", fontFamily: F.body, fontSize: 28, color: C.ink2, opacity: igual }}>
        Para el pasajero nada cambia; <b style={{ color: C.ink }}>cada llamada ya queda registrada.</b>
      </div>

      <div style={{ ...card, left: 120, top: 640, width: 820, height: 280, padding: "28px 36px", borderLeft: `10px solid ${C.accent}`, ...sube(base) }}>
        <Rotulo>Resultado: la línea de base</Rotulo>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, lineHeight: 1.12, color: C.ink, marginTop: 14 }}>Cuántas llamadas entran, cuántas se atienden y cómo.</div>
        <div style={{ fontFamily: F.body, fontSize: 26, color: C.ink2, marginTop: 12 }}>Contra ese registro se mide después cuánto mejora.</div>
      </div>
      <div style={{ ...card, left: 980, top: 640, width: 820, height: 280, padding: "28px 36px", borderLeft: `10px solid ${C.accent}`, ...sube(aprende) }}>
        <Rotulo>De qué hablan sus clientes</Rotulo>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, lineHeight: 1.12, color: C.ink, marginTop: 14 }}>Escuchamos las conversaciones reales.</div>
        <div style={{ fontFamily: F.body, fontSize: 26, lineHeight: 1.3, color: C.ink2, marginTop: 12 }}>Y configuramos el agente a la medida de cómo ya trabajan en cada sucursal.</div>
      </div>

      <Paquete t={t} curva={F1} a={en("a7", "las llamadas pasan")} b={en("a7", "nuestro sistema") + 0.2}><Wave n={4} h={20} /></Paquete>
      <Paquete t={t} curva={F2} a={en("a7", "directo a la persona")} b={en("a7", "sin agente") + 0.1}><Wave n={4} h={20} /></Paquete>
      <Pie />
    </AbsoluteFill>
  );
};

// ---------- 5. Etapa 2: sucursal por sucursal ----------

export const Etapa2: React.FC = () => {
  const t = useT();
  const a = en("a9", "el agente se suma");
  const b = en("a9", "y comparamos");
  const tiles = SUC.map((_, i) => useIn(0.15 + i * 0.08, 0.4));
  const on = SUC.map((_, i) => interpolate(t, [a + ((b - a) * i) / 6, a + ((b - a) * i) / 6 + 0.3], [0, 1], { ...CLAMP, easing: EASE }));
  const comp = useIn(b - 0.1, 0.5);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Etapa 2 · sucursal por sucursal" text="Implementación escalonada," accent="contra la línea de base." />
      <div style={{ position: "absolute", left: 120, right: 120, top: 300, display: "flex", gap: 20 }}>
        {SUC.map((n, i) => {
          const o = on[i] > 0.5;
          return (
            <div key={n} style={{
              flex: 1, height: 280, boxSizing: "border-box", padding: "22px 18px", display: "flex", flexDirection: "column", alignItems: "center", gap: 14, borderRadius: 24,
              background: o ? C.accentSoft : "#fff", border: `2px solid ${o ? C.accent : C.line}`, boxShadow: shadowCard, ...sube(tiles[i], 20),
              transform: `translateY(${(1 - tiles[i]) * 20}px) scale(${1 + 0.03 * on[i]})`,
            }}>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Sucursal {n}</div>
              <div style={{ position: "relative", width: 110, height: 110 }}>
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: 1 - on[i] }}>
                  <Baldosa size={84} gris><Icon name="store" size={46} color="#fff" /></Baldosa>
                </div>
                <div style={{ position: "absolute", inset: 0, opacity: on[i], transform: `scale(${0.7 + 0.3 * on[i]})` }}>
                  <AgenteLogo size={110} />
                </div>
              </div>
              <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 23, color: o ? C.accent2 : C.muted, textAlign: "center" }}>{o ? "Con el agente" : "Directo a la persona"}</div>
            </div>
          );
        })}
      </div>
      <div style={{ ...card, left: 120, top: 640, width: 1680, height: 280, padding: "30px 40px", border: `2px solid ${C.accent}`, background: C.accentSoft, ...sube(comp) }}>
        <Rotulo>Cada resultado se compara contra la línea de base</Rotulo>
        <div style={{ display: "flex", gap: 16, marginTop: 20 }}>
          {["Llamadas atendidas", "Perdidas", "Derivadas"].map((x) => (
            <div key={x} style={{ padding: "14px 26px", borderRadius: 999, background: "#fff", border: `2px solid ${C.line2}`, fontFamily: F.body, fontWeight: 800, fontSize: 30, color: C.ink, whiteSpace: "nowrap" }}>{x}</div>
          ))}
        </div>
        <div style={{ fontFamily: F.body, fontSize: 27, lineHeight: 1.3, color: C.ink2, marginTop: 22 }}>
          Cada sucursal arranca con lo aprendido en la etapa 1 y en las anteriores. Las personas siguen atendiendo lo que necesita una persona.
        </div>
      </div>
      <Pie />
    </AbsoluteFill>
  );
};

// ---------- 6. Cómo funciona: sus números → agente → teléfono IP de la sucursal (PDF v2, hoja 2) ----------

const RY = 500;
const AG2 = { x: 1110, y: RY };
const R2 = 100;
const G1: Curva = recta({ x: 440, y: RY }, { x: 510, y: RY });
const G2: Curva = recta({ x: 860, y: RY }, { x: AG2.x - R2 - 10, y: RY });
const G3: Curva = recta({ x: AG2.x + R2 + 10, y: RY }, { x: 1440, y: RY });

export const Funciona: React.FC = () => {
  const t = useT();
  const n1 = useIn(0.15, 0.45);
  const n2 = useIn(en("a10", "sus números") - 0.1, 0.45);
  const fijo = interpolate(t, [en("a10", "fijo o"), en("a10", "fijo o") + 0.3], [0, 1], CLAMP);
  const ag = usePop(en("a10", "El agente atiende") - 0.1);
  const rot = useIn(en("a10", "El agente atiende"), 0.5);
  const n4 = useIn(en("a10", "pasa al teléfono") - 0.1, 0.45);
  const bL = useIn(en("a10", "El agente atiende") - 0.3, 0.5);
  const bR = useIn(en("a10", "que se instala") - 0.1, 0.5);
  const talk = useHabla("a10", AT.a10, 0.3);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Cómo funciona" text="Sus números de siempre," accent="y una persona si hace falta." size={60} />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Traza curva={G1} o={n2} />
        <Traza curva={G2} o={rot} />
        <Traza curva={G3} o={n4} dash="12 12" />
      </svg>
      <Nodo left={120} top={RY - 80} w={320} h={160} p={n1} icono={<Baldosa size={54}><Pasajero size={32} /></Baldosa>} titulo="El pasajero" sub="llama como hoy" />
      <div style={{ ...card, left: 510, top: RY - 85, width: 350, height: 170, padding: "16px 26px", border: `2px solid ${fijo > 0.5 ? C.accent : C.line}`, ...sube(n2, 20) }}>
        <Rotulo style={{ fontSize: 18 }}>Sus números</Rotulo>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 31, lineHeight: 1.1, color: C.ink, marginTop: 6 }}>El fijo de siempre<br /><span style={{ color: C.accent }}>o un 0800</span></div>
        <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink2, marginTop: 6 }}>los mismos de hoy</div>
      </div>

      <div style={{ position: "absolute", left: AG2.x - 200, width: 400, top: RY - R2 - 70, display: "flex", justifyContent: "center", gap: 12, alignItems: "center", opacity: rot }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Agente de IA</div>
        <div style={{ padding: "4px 14px", background: C.accentSoft, border: "2px solid #c9d6fb", borderRadius: 999, fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.accent2 }}>24 horas</div>
      </div>
      <Aro t={t} cx={AG2.x} cy={AG2.y} r={R2} on={rot} />
      <div style={{ position: "absolute", left: AG2.x - 75, top: AG2.y - 75, transform: `scale(${ag})` }}>
        <AgenteLogo size={150} talk={talk} />
      </div>
      <div style={{ position: "absolute", left: AG2.x - 230, width: 460, top: AG2.y + R2 + 24, textAlign: "center", fontFamily: F.body, fontSize: 23, lineHeight: 1.3, color: C.ink2, opacity: rot }}>
        Consulta horarios y disponibilidad.<br />Registra cada llamada.
      </div>
      <div style={{ position: "absolute", left: 1240, width: 200, top: RY - 52, textAlign: "center", fontFamily: F.body, fontWeight: 800, fontSize: 22, color: C.accent, opacity: n4 }}>si hace falta</div>
      <div style={{ ...card, left: 1440, top: RY - 95, width: 360, height: 190, padding: "20px 24px", border: `2px solid ${n4 > 0.5 ? C.accent : C.line}`, ...sube(n4, 20) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Baldosa size={60}><TelefonoIP size={38} /></Baldosa>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>La sucursal</div>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 23, lineHeight: 1.28, color: C.ink2, marginTop: 12 }}>En su teléfono IP atiende una persona, con el motivo ya anotado.</div>
      </div>

      <div style={{ ...card, left: 120, top: 760, width: 820, height: 180, padding: "26px 34px", ...sube(bL) }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Conservan sus números de siempre.</div>
        <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.3, color: C.ink2, marginTop: 8 }}>Sus pasajeros llaman como hoy; la llamada se desvía al agente, y se puede sumar un 0800 para toda la red.</div>
      </div>
      <div style={{ ...card, left: 980, top: 760, width: 820, height: 180, padding: "26px 34px", ...sube(bR) }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Un teléfono IP en cada sucursal.</div>
        <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.3, color: C.ink2, marginTop: 8 }}>Se instala uno que recibe las llamadas que el agente pasa a una persona, con el motivo ya anotado.</div>
      </div>

      <Paquete t={t} curva={G2} a={en("a10", "El agente atiende")} b={en("a10", "El agente atiende") + 0.7}><Wave n={4} h={20} /></Paquete>
      <Paquete t={t} curva={G3} a={en("a10", "pasa al teléfono")} b={en("a10", "pasa al teléfono") + 0.9}>motivo</Paquete>
      <Pie />
    </AbsoluteFill>
  );
};

// ---------- 7. Próximos pasos (PDF v2, hoja 2) ----------

const PASOS = [
  { t: "Las 6 sucursales", s: "Confirmar cuáles son, quién atiende en cada una y en qué horario.", at: en("a11", "las sucursales") },
  { t: "Horarios y disponibilidad", s: "Acceso a esa información, o la forma de consultarla, para que el agente diga lo vigente.", at: en("a11", "los horarios") },
  { t: "El desvío de las líneas", s: "Se activa desde el mismo teléfono, con un código: cada número pasa a nuestro sistema.", at: en("a11", "el desvío") },
];

export const Pasos: React.FC = () => {
  const ins = PASOS.map((p) => useIn(p.at - 0.15, 0.45));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Próximos pasos" text="Para arrancar" accent="en 10 días." />
      <div style={{ position: "absolute", left: 120, right: 120, top: 270, display: "flex", gap: 24 }}>
        {PASOS.map((p, i) => (
          <div key={p.t} style={{ flex: 1, height: 400, boxSizing: "border-box", padding: "34px 36px", background: "#fff", border: `2px solid ${C.line}`, borderRadius: 24, boxShadow: shadowCard, ...sube(ins[i], 30) }}>
            <div style={{ width: 64, height: 64, borderRadius: 32, background: C.accent, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.display, fontWeight: 800, fontSize: 36 }}>{i + 1}</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 42, lineHeight: 1.1, color: C.ink, marginTop: 26 }}>{p.t}</div>
            <div style={{ fontFamily: F.body, fontSize: 29, lineHeight: 1.32, color: C.ink2, marginTop: 16 }}>{p.s}</div>
          </div>
        ))}
      </div>
      <Pie />
    </AbsoluteFill>
  );
};

// ---------- 8. Cierre en blanco: la frase del PDF y el contacto ----------

export const Cierre: React.FC = () => {
  const logo = usePop(0.1);
  const line = useIn(AT.a12 - 0.2, 0.6);
  const contacto = useIn(AT.a12 + 1.2, 0.5);
  const invita = useIn(AT.a13 - 0.1, 0.5);
  // Fundido final de la imagen (la música se desvanece en el mismo tramo, en Montaje)
  const t = useT();
  const L = CIERRE_LEN;
  const fin = interpolate(t, [L - 1.4, L - 0.2], [1, 0], CLAMP);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill style={{ opacity: fin }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 190, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 340 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 360, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 100, lineHeight: 1.08, color: C.ink, letterSpacing: "-0.02em", ...sube(line, 24),
      }}>
        Cada llamada atendida,<br /><span style={{ color: C.accent }}>cada llamada medida.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 690, textAlign: "center", opacity: contacto }}>
        <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 32, color: C.ink }}>Contacto: Laureano Arcanio</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 64, color: C.ink, marginTop: 14 }}>0800-220-1233</div>
        <div style={{ fontFamily: F.mono, fontSize: 27, color: C.muted, marginTop: 14 }}>atentina.com.ar · laureano@atentina.com.ar · WhatsApp +54 9 351 700-2592</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 952, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.accent, ...sube(invita, 14) }}>
        ¿Damos juntos el primer paso?
      </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

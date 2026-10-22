import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import dur from "../../../public/proyectos/goldman/vo/duraciones.json";
import envs from "../../../public/proyectos/goldman/vo/envolventes.json";
import { AgenteLogo, CAST, Person } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { Card, Headline, Icon, Link, useIn, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

// Momentos de g3 (s desde que arranca la voz), por las pausas de la toma
const M = { cero800: 3.4, wa: 5.1, web: 6.1, clasifica: 7.2, responde: 8.03, deriva: 9.47 };

const CANALES = [
  { icon: "phone" as const, titulo: "Línea 0800 / 0810", texto: "Atiende y pasa la llamada a un vendedor", y: 290, at: M.cero800 },
  { icon: "wa" as const, titulo: "WhatsApp", texto: "Responde y deriva al WhatsApp de un vendedor o de soporte", y: 500, at: M.wa },
  { icon: "web" as const, titulo: "Chat en su web", texto: "Sabe qué producto está mirando y pasa a una persona", y: 710, at: M.web },
];
const TIPOS = ["Ventas", "Instalaciones", "Productos", "Precios"];

// Centro del agente y bordes de las columnas
const AG = { x: 980, y: 455 };
const IZQ = 680;
const DER = 1300;

type P = { x: number; y: number };
const bez = (a: P, c: P, b: P, k: number): P => ({
  x: (1 - k) * (1 - k) * a.x + 2 * (1 - k) * k * c.x + k * k * b.x,
  y: (1 - k) * (1 - k) * a.y + 2 * (1 - k) * k * c.y + k * k * b.y,
});
const curva = (a: P, b: P) => {
  const c = { x: (a.x + b.x) / 2, y: a.y };
  return { c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` };
};

const ENTRADAS = CANALES.map((c) => curva({ x: IZQ, y: c.y + 95 }, { x: AG.x - 110, y: AG.y }));
const RESPONDE = { x: DER, y: 405 };
const DERIVA = { x: DER, y: 735 };
const SALIDA_R = curva({ x: AG.x + 110, y: AG.y }, RESPONDE);
const SALIDA_D = curva({ x: AG.x + 110, y: AG.y }, DERIVA);

/** Paquete que viaja por una curva entre `t0` y `t1` (s de escena). */
const Paquete: React.FC<{ a: P; c: P; b: P; t0: number; t1: number; icon: "wa" | "phone" | "check" }> = ({ a, c, b, t0, t1, icon }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const k = interpolate(t, [t0, t1], [0, 1], { ...CLAMP, easing: EASE });
  const o = interpolate(t, [t0 - 0.1, t0, t1, t1 + 0.25], [0, 1, 1, 0], CLAMP);
  const p = bez(a, c, b, k);
  return (
    <div style={{
      position: "absolute", left: p.x - 30, top: p.y - 30, width: 60, height: 60, borderRadius: 30, opacity: o,
      background: icon === "wa" ? C.wa : C.accent, display: "flex", alignItems: "center", justifyContent: "center",
      boxShadow: "0 8px 22px rgba(36,86,230,.35)",
    }}>
      <Icon name={icon} size={30} color="#fff" />
    </div>
  );
};

/** 2. La propuesta: los tres canales, el agente que clasifica, responde y deriva. */
export const Propuesta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.g3 + s;
  const agente = usePop(v(0.3));
  const canales = CANALES.map((c) => useIn(v(c.at), 0.5));
  const tipos = TIPOS.map((_, i) => usePop(v(M.clasifica) + i * 0.12));
  const responde = useIn(v(M.responde), 0.5);
  const deriva = useIn(v(M.deriva), 0.5);
  // El agente habla (las barras) mientras suena la locución, a modo de "atiende"
  const env = envs.g3;
  const i = frame - Math.round(v(0) * fps);
  const talk = i >= 0 && i < env.length && t < v(dur.g3) ? env[i] * 0.6 : 0;
  // "Precios" se marca cuando llega la consulta del WhatsApp
  const marca = interpolate(t, [v(M.clasifica) + 0.55, v(M.clasifica) + 0.8], [0, 1], CLAMP);
  const activo = (x: number) => 1 + 0.04 * x;
  return (
    <AbsoluteFill>
      <Headline eyebrow="La propuesta" text="El especialista de guardia," accent="en los tres canales." />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRADAS.map((e, k) => <Link key={k} d={e.d} color={C.accent} opacity={canales[k] * 0.5} />)}
        <Link d={SALIDA_R.d} color={C.ok} opacity={responde * 0.6} />
        <Link d={SALIDA_D.d} color={C.accent} opacity={deriva * 0.6} />
      </svg>

      {CANALES.map((c, k) => (
        <Card key={c.titulo} style={{
          position: "absolute", left: 120, top: c.y, width: 560, height: 190, padding: "26px 30px", boxSizing: "border-box",
          opacity: canales[k], transform: `translateX(${(1 - canales[k]) * -40}px)`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ width: 64, height: 64, borderRadius: 32, background: c.icon === "wa" ? C.okSoft : C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon name={c.icon} size={34} color={c.icon === "wa" ? C.wa : C.accent} />
            </div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink }}>{c.titulo}</div>
          </div>
          <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.3, color: C.ink2, marginTop: 14 }}>{c.texto}</div>
        </Card>
      ))}

      {/* El agente: el logo de Atentina */}
      <div style={{ position: "absolute", left: AG.x - 110, top: AG.y - 110, width: 220, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente})` }}>
        <AgenteLogo size={220} talk={talk} style={{ filter: "drop-shadow(0 16px 30px rgba(36,86,230,.22))" }} />
        <div style={{ marginTop: 14, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 21, whiteSpace: "nowrap" }}>
          Especialista de guardia · 24/7
        </div>
      </div>

      {/* Clasifica */}
      <div style={{ position: "absolute", left: AG.x - 215, top: 680, width: 430, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {TIPOS.map((x, k) => {
          const on = x === "Precios" ? marca : 0;
          return (
            <div key={x} style={{
              textAlign: "center", borderRadius: 999, padding: "10px 0", fontFamily: F.body, fontWeight: 700, fontSize: 24,
              background: on > 0.5 ? C.accent : "#fff", color: on > 0.5 ? "#fff" : C.ink2, border: `2px solid ${on > 0.5 ? C.accent : C.line}`,
              transform: `scale(${tipos[k] * activo(on)})`,
            }}>
              {x}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: AG.x - 215, width: 430, top: 820, textAlign: "center", fontFamily: F.mono, fontSize: 20, color: C.muted, opacity: tipos[0] }}>
        clasifica cada consulta
      </div>

      {/* Responde lo general */}
      <Card style={{ position: "absolute", left: DER, top: 290, width: 500, height: 230, padding: "26px 30px", boxSizing: "border-box", opacity: responde, transform: `translateX(${(1 - responde) * 40}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 54, height: 54, borderRadius: 27, background: C.okSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="check" size={30} color={C.ok} />
          </div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Responde lo general</div>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 24, lineHeight: 1.45, color: C.ink2, marginTop: 14 }}>
          Modelos y frigorías · Instalación<br />Horarios y formas de pago · Cursos
        </div>
      </Card>

      {/* Deriva a su equipo */}
      <Card style={{ position: "absolute", left: DER, top: 560, width: 500, height: 350, padding: "26px 30px", boxSizing: "border-box", opacity: deriva, transform: `translateX(${(1 - deriva) * 40}px)`, overflow: "hidden" }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Deriva a su equipo</div>
        <div style={{ display: "flex", justifyContent: "space-around", marginTop: 10 }}>
          {[{ who: "Vendedor", cast: CAST.otro }, { who: "Soporte", cast: CAST.cliente2 }].map((p) => (
            <div key={p.who} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <Person {...p.cast} size={140} mood="happy" />
              <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.ink, marginTop: 4 }}>{p.who}</div>
            </div>
          ))}
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 20, color: C.muted, textAlign: "center", marginTop: 10 }}>con la ficha de lo hablado</div>
      </Card>

      {/* Viajes: una consulta de WhatsApp que se responde y una llamada que se deriva */}
      <Paquete a={{ x: IZQ, y: CANALES[1].y + 95 }} c={ENTRADAS[1].c} b={{ x: AG.x - 110, y: AG.y }} t0={v(M.clasifica - 0.1)} t1={v(M.clasifica + 0.6)} icon="wa" />
      <Paquete a={{ x: AG.x + 110, y: AG.y }} c={SALIDA_R.c} b={RESPONDE} t0={v(M.responde)} t1={v(M.responde + 0.7)} icon="check" />
      <Paquete a={{ x: IZQ, y: CANALES[0].y + 95 }} c={ENTRADAS[0].c} b={{ x: AG.x - 110, y: AG.y }} t0={v(M.deriva - 0.6)} t1={v(M.deriva)} icon="phone" />
      <Paquete a={{ x: AG.x + 110, y: AG.y }} c={SALIDA_D.c} b={DERIVA} t0={v(M.deriva + 0.1)} t1={v(M.deriva + 0.8)} icon="phone" />
    </AbsoluteFill>
  );
};

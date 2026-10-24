import React from "react";
import { AbsoluteFill, interpolate, interpolateColors, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Person } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Icon } from "../../../src/comun/ui";
import {
  CANAL, CLIENTES, CX, CY, FILA_AT, filaY, MENSAJES, Mensaje, N_PUNTOS, OPERADORA, R, T, TITULOS, VIAJE, VUELTA,
  VUELTA_EQUIPO,
} from "./timeline";

/**
 * Video de la landing (horizontal, sin locución, en loop): el logo en el centro con un aro de puntos que gira
 * como la espera del agente; los clientes de la izquierda mandan consultas que entran al aro, dan la vuelta y
 * vuelven resueltas; solo las importantes salen hacia la operadora de la derecha, que le responde al cliente.
 */

const TAU = Math.PI * 2;
const OMEGA = TAU / VUELTA;
const OP_X = 1360; // borde izquierdo del panel de la operadora
const OP_CARD_Y = [500, 625];
const ANCHO_FILA = 730; // de donde sale y adonde vuelve el paquete de cada cliente

type P = { x: number; y: number };
const lerp = (a: P, b: P, k: number): P => ({ x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k });
const bez = (a: P, c: P, b: P, k: number): P => ({
  x: (1 - k) ** 2 * a.x + 2 * (1 - k) * k * c.x + k ** 2 * b.x,
  y: (1 - k) ** 2 * a.y + 2 * (1 - k) * k * c.y + k ** 2 * b.y,
});
const enAro = (th: number): P => ({ x: CX + R * Math.cos(th), y: CY + R * Math.sin(th) });
const ease = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], { ...CLAMP, easing: EASE });
const fade = (t: number, a: number, b: number, dur = 0.35) =>
  Math.min(interpolate(t, [a, a + dur], [0, 1], CLAMP), interpolate(t, [b - dur, b], [1, 0], CLAMP));

// Plan de cada mensaje: cuándo sale, cuándo entra al aro, cuándo sale y adónde va
type Plan = Mensaje & {
  i: number; dep: number; tIn: number; tOut: number; thIn: number; qPt: P; rPt: P;
  llega: number; // la respuesta llega al cliente
  op?: { card: number; llega: number; sale: number };
};

const planes: Plan[] = (() => {
  const out: Plan[] = [];
  let listoOp = T.operadorIn + 0.4;
  let card = 0;
  MENSAJES.forEach((m, i) => {
    const y = filaY(m.fila);
    const qPt = { x: ANCHO_FILA, y: y - 11 };
    const rPt = { x: ANCHO_FILA, y: y + 43 };
    const thIn = Math.atan2(qPt.y - CY, qPt.x - CX);
    const dep = m.qAt + 0.6;
    const tIn = dep + VIAJE;
    if (!m.derivada) {
      const tOut = tIn + VUELTA;
      out.push({ ...m, i, dep, tIn, tOut, thIn, qPt, rPt, llega: tOut + VIAJE });
      return;
    }
    // Derivada: sigue girando hasta que la operadora está y sale por la derecha (ángulo 0)
    let k = 1;
    let tOut = tIn + (TAU * k - thIn) / OMEGA;
    while (tOut < Math.max(listoOp, tIn + VUELTA)) tOut = tIn + (TAU * ++k - thIn) / OMEGA;
    listoOp = tOut + 0.6;
    const opLlega = tOut + VIAJE;
    const opSale = opLlega + 1.4;
    out.push({ ...m, i, dep, tIn, tOut, thIn, qPt, rPt, llega: opSale + VUELTA_EQUIPO, op: { card: card++, llega: opLlega, sale: opSale } });
  });
  return out;
})();

// Hasta cuándo se ve cada mensaje en su fila: hasta la siguiente consulta del mismo cliente o la salida
const hasta = (p: Plan) => {
  const sig = planes.find((o) => o.fila === p.fila && o.qAt > p.qAt);
  return sig ? sig.qAt - 0.1 : T.salida + 0.6;
};

type Paquete = { pt: P; tipo: "canal" | "resuelta" | "equipo" | "derivada"; enAro: boolean };
const paquete = (p: Plan, t: number): Paquete | null => {
  if (t < p.dep) return null;
  const tipoIda = p.derivada && t > p.tIn + 1.0 ? "derivada" : "canal";
  if (t < p.tIn) return { pt: lerp(p.qPt, enAro(p.thIn), ease(t, p.dep, p.tIn)), tipo: "canal", enAro: false };
  if (t < p.tOut) return { pt: enAro(p.thIn + OMEGA * (t - p.tIn)), tipo: tipoIda, enAro: true };
  if (!p.op) {
    if (t < p.llega) return { pt: lerp(enAro(p.thIn), p.rPt, ease(t, p.tOut, p.llega)), tipo: "resuelta", enAro: false };
    return null;
  }
  const card = { x: OP_X, y: OP_CARD_Y[p.op.card] };
  if (t < p.op.llega) return { pt: lerp(enAro(0), card, ease(t, p.tOut, p.op.llega)), tipo: "derivada", enAro: false };
  if (t < p.op.sale) return null;
  if (t < p.llega) {
    const ctrl = { x: 1100, y: p.op.card === 0 ? 1080 : 1110 };
    return { pt: bez(card, ctrl, p.rPt, ease(t, p.op.sale, p.llega)), tipo: "equipo", enAro: false };
  }
  return null;
};

/** El paquete que viaja: ícono del canal a la ida, check a la vuelta. */
const Chip: React.FC<{ p: Paquete; canal: keyof typeof CANAL; s: number }> = ({ p, canal, s }) => {
  const frame = useCurrentFrame();
  const color = canal === "wa" ? C.wa : canal === "phone" ? C.accent : C.ink;
  const estilos = {
    canal: { bg: color, fg: "#fff", borde: color, icon: canal === "wa" ? "wa" : canal === "phone" ? "phone" : "web" },
    derivada: { bg: C.ok, fg: "#fff", borde: C.ok, icon: "users" },
    resuelta: { bg: "#fff", fg: C.accent, borde: C.accent, icon: "check" },
    equipo: { bg: C.okSoft, fg: C.ok, borde: C.ok, icon: "check" },
  } as const;
  const e = estilos[p.tipo];
  const halo = p.tipo === "derivada" ? 0.5 + 0.5 * Math.sin(frame / 4) : 0;
  return (
    <div style={{
      position: "absolute", left: p.pt.x - 30, top: p.pt.y - 21, width: 60, height: 42, borderRadius: 14, background: e.bg,
      border: `2.5px solid ${e.borde}`, display: "grid", placeItems: "center", transform: `scale(${s})`,
      boxShadow: halo ? `0 0 0 ${4 + halo * 6}px rgba(27, 156, 91, ${0.25 - halo * 0.12})` : shadowCard,
    }}>
      <Icon name={e.icon} size={26} color={e.fg} />
    </div>
  );
};

/** Busto dentro de un círculo. */
const Avatar: React.FC<{ cast: string; size: number }> = ({ cast, size }) => {
  const c = cast === "mayor"
    ? { skin: "#e6b99a", hair: "#a7afb8", hairStyle: "short", top: "#b5835a", topDark: "#8f6443", glasses: true }
    : cast === "operadora" ? CAST.duena : CAST[cast as keyof typeof CAST];
  const h = size * 1.3;
  return (
    <div style={{ width: size, height: size, borderRadius: "50%", overflow: "hidden", background: C.surface2, position: "relative", flex: "none" }}>
      <div style={{ position: "absolute", left: size * 0.5 - h * 0.4, top: size * 0.47 - (118 / 300) * h }}>
        <Person {...(c as React.ComponentProps<typeof Person>)} size={h} mood="happy" blinkOffset={cast.length * 13} />
      </div>
    </div>
  );
};

const Globo: React.FC<{ tipo: "q" | "r" | "equipo"; children: React.ReactNode; o: number; s: number }> = ({ tipo, children, o, s }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 10, opacity: o, transform: `scale(${s})`, transformOrigin: "left center",
    background: tipo === "q" ? "#fff" : tipo === "r" ? C.accentSoft : C.okSoft,
    border: tipo === "q" ? `2px solid ${C.line}` : "2px solid transparent", borderRadius: 18, padding: "6px 16px",
    fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.ink, whiteSpace: "nowrap", height: 46, boxSizing: "border-box",
  }}>
    {children}
  </div>
);

const Isotipo: React.FC<{ size: number; barras?: number[] }> = ({ size, barras = [12, 22, 12] }) => (
  <svg viewBox="0 0 64 64" width={size} height={size}>
    <path d="M55.07 38.62A24 24 0 1 1 55.07 25.38" fill="none" stroke={C.ink} strokeWidth={8} strokeLinecap="round" />
    {barras.map((v, i) => <rect key={i} x={20 + i * 9} y={32 - v / 2} width={6} height={v} rx={3} fill={C.accent} />)}
  </svg>
);

const Fila: React.FC<{ i: number; t: number; pop: (at: number) => number }> = ({ i, t, pop }) => {
  const cl = CLIENTES[i];
  const y = filaY(i);
  const ap = ease(t, FILA_AT[i], FILA_AT[i] + 0.6);
  const sale = 1 - ease(t, T.salida, T.salida + 0.6);
  const msgs = planes.filter((p) => p.fila === i);
  // Estado de la fila según el último mensaje que ya salió
  const actual = [...msgs].reverse().find((p) => t >= p.qAt);
  let estado = "";
  let colorEstado: string = C.muted;
  if (actual && t >= actual.dep) {
    if (t >= actual.llega) {
      estado = actual.op ? `resuelta · ${OPERADORA.nombre}` : "resuelta";
      colorEstado = actual.op ? C.ok : C.accent;
    } else if (actual.op && t >= actual.op.llega) {
      estado = `con ${OPERADORA.nombre}`;
      colorEstado = C.ok;
    } else if (actual.derivada && t >= actual.tIn + 1.0) {
      estado = "para tu equipo";
      colorEstado = C.ok;
    } else estado = "atendiendo";
  }
  return (
    <div style={{ position: "absolute", left: 60, top: y - 70, height: 150, display: "flex", gap: 22, alignItems: "center", opacity: ap * sale, transform: `translateX(${(1 - ap) * -40}px)` }}>
      <Avatar cast={cl.cast} size={104} />
      <div style={{ position: "relative", width: 540, height: 150 }}>
        <div style={{ position: "absolute", top: 4, left: 2, display: "flex", alignItems: "center", gap: 10, fontFamily: F.mono, fontSize: 19, letterSpacing: "0.04em", color: C.muted, whiteSpace: "nowrap" }}>
          <Icon name={cl.canal === "phone" ? "phone" : cl.canal} size={22} color={cl.canal === "wa" ? C.wa : cl.canal === "phone" ? C.accent : C.ink} />
          <span style={{ color: C.ink2, textTransform: "uppercase" }}>{cl.nombre} · {CANAL[cl.canal]}</span>
          {estado ? <span style={{ color: colorEstado, marginLeft: 6 }}>{estado}</span> : null}
        </div>
        {msgs.map((p) => {
          const fin = hasta(p);
          if (t < p.qAt || t > fin) return null;
          const oq = interpolate(t, [fin - 0.3, fin], [1, 0], CLAMP);
          return (
            <React.Fragment key={p.i}>
              <div style={{ position: "absolute", top: 36, left: 0 }}>
                <Globo tipo="q" o={oq} s={pop(p.qAt)}>{p.q}</Globo>
              </div>
              {t >= p.llega ? (
                <div style={{ position: "absolute", top: 90, left: 26 }}>
                  <Globo tipo={p.op ? "equipo" : "r"} o={oq} s={pop(p.llega)}>
                    {p.op ? <b style={{ color: C.ok }}>{OPERADORA.nombre}:</b> : <Isotipo size={26} />}
                    {p.r}
                  </Globo>
                </div>
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

const Operadora: React.FC<{ t: number; pop: (at: number) => number }> = ({ t, pop }) => {
  const ap = ease(t, T.operadorIn, T.operadorIn + 0.7);
  const sale = 1 - ease(t, T.salida, T.salida + 0.6);
  const derivadas = planes.filter((p) => p.op);
  return (
    <div style={{
      position: "absolute", left: OP_X, top: 300, width: 510, height: 400, opacity: ap * sale, transform: `translateX(${(1 - ap) * 50}px)`,
      background: "#fff", border: `2px solid ${C.line}`, borderRadius: 28, boxShadow: shadowCard, boxSizing: "border-box",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20, padding: "22px 26px", borderBottom: `2px solid ${C.line}` }}>
        <Avatar cast="operadora" size={96} />
        <div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ink, letterSpacing: "-0.015em" }}>{OPERADORA.nombre}</div>
          <div style={{ fontFamily: F.mono, fontSize: 19, letterSpacing: "0.08em", textTransform: "uppercase", color: C.ok, marginTop: 2 }}>{OPERADORA.rol}</div>
        </div>
      </div>
      {derivadas.map((p) => {
        const op = p.op!;
        const s = pop(op.llega);
        const listo = t >= op.sale;
        return (
          <div key={p.i} style={{
            position: "absolute", left: 22, right: 22, top: OP_CARD_Y[op.card] - 300 - 48, height: 96, opacity: t >= op.llega ? 1 : 0,
            transform: `scale(${s})`, borderRadius: 16, border: `2px solid ${listo ? C.line : C.ok}`, background: listo ? "#fff" : C.okSoft,
            display: "flex", alignItems: "center", gap: 16, padding: "0 18px", boxSizing: "border-box",
          }}>
            <div style={{ width: 52, height: 52, borderRadius: 14, background: C.ok, display: "grid", placeItems: "center", flex: "none" }}>
              <Icon name="phone" size={26} color="#fff" />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 27, color: C.ink }}>{p.derivada!.titulo}</div>
              <div style={{ fontFamily: F.body, fontWeight: 500, fontSize: 20, color: C.muted, whiteSpace: "nowrap" }}>{p.derivada!.detalle}</div>
            </div>
            <div style={{ fontFamily: F.mono, fontSize: 17, color: listo ? C.ok : C.ink2, whiteSpace: "nowrap" }}>{listo ? "respondida" : "en curso"}</div>
          </div>
        );
      })}
    </div>
  );
};

const Titulo: React.FC<{ t: number }> = ({ t }) => (
  <>
    {TITULOS.map((x, i) => {
      const o = fade(t, x.de, x.a, 0.45);
      if (o <= 0) return null;
      const final = i === TITULOS.length - 1;
      return (
        // Durante la acción el título va arriba a la derecha (sobre la operadora), fuera del camino de los paquetes;
        // el del cierre, centrado arriba del logo
        <div key={i} style={{
          position: "absolute", left: final ? CX - 380 : OP_X, width: final ? 760 : 510, top: 70, textAlign: final ? "center" : "left",
          opacity: o, transform: `translateY(${(1 - Math.min(1, o * 1.4)) * 16}px)`,
        }}>
          <div style={{ fontFamily: F.mono, fontSize: 22, letterSpacing: "0.08em", textTransform: "uppercase", color: C.accent }}>{x.rotulo}</div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: final ? 56 : 50, lineHeight: 1.08, letterSpacing: "-0.015em", color: C.ink, marginTop: 12, textWrap: "balance" }}>
            {x.texto} <span style={{ color: C.accent, display: final ? "block" : "inline" }}>{x.acento}</span>
          </div>
        </div>
      );
    })}
  </>
);

const Contador: React.FC<{ t: number }> = ({ t }) => {
  const resueltas = planes.filter((p) => !p.op && t >= p.llega).length;
  const derivadas = planes.filter((p) => p.op && t >= p.op.llega).length;
  const primera = Math.min(...planes.map((p) => p.llega));
  const o = fade(t, primera - 0.2, T.cierreOut, 0.4);
  const num = { fontFamily: F.display, fontWeight: 800, fontSize: 40, fontVariantNumeric: "tabular-nums" } as const;
  return (
    <div style={{ position: "absolute", left: CX - 260, width: 520, top: CY + R + 66, opacity: o, display: "flex", justifyContent: "center", alignItems: "baseline", gap: 14, fontFamily: F.mono, fontSize: 22, color: C.muted, whiteSpace: "nowrap" }}>
      <span style={{ ...num, color: C.accent }}>{resueltas}</span> resueltas
      <span style={{ color: C.line2 }}>·</span>
      <span style={{ ...num, color: C.ok, opacity: derivadas ? 1 : 0.35 }}>{derivadas}</span> derivadas
    </div>
  );
};

export const LandingAgenteVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pop = (at: number) => spring({ frame: frame - at * fps, fps, config: { damping: 14, stiffness: 170 } });

  const paquetes = planes.map((p) => ({ p, q: paquete(p, t) }));
  const enGiro = paquetes.filter((x) => x.q?.enAro).length;

  // Aro de puntos: aparece punto por punto, gira como una espera y se va al revés
  const cabeza = (t * TAU) / 2.4;
  const actividad = interpolate(enGiro, [0, 3], [0.55, 1], CLAMP);
  const puntos = Array.from({ length: N_PUNTOS }).map((_, i) => {
    const th = (i / N_PUNTOS) * TAU - Math.PI / 2;
    const entra = spring({ frame: frame - (T.aroIn + i * 0.02) * fps, fps, config: { damping: 12, stiffness: 180 } });
    const sale = 1 - ease(t, T.aroOut + (N_PUNTOS - 1 - i) * 0.02, T.aroOut + (N_PUNTOS - 1 - i) * 0.02 + 0.3);
    const d = (((cabeza - (th + Math.PI / 2)) % TAU) + TAU) % TAU;
    const k = Math.max(0, 1 - d / (TAU * 0.32)) * actividad;
    return { x: CX + R * Math.cos(th), y: CY + R * Math.sin(th), s: entra * sale, k };
  });

  // Logo: entra con un pop; las barras se mueven más cuanto más consultas hay girando
  const logoS = pop(T.logoIn) * (1 - ease(t, T.logoOut, T.logoOut + 0.5));
  const amp = interpolate(enGiro, [0, 1, 4], [0.12, 0.45, 0.8], CLAMP);
  const barras = [12, 22, 12].map((b, i) => Math.min(30, b * (1 + amp * (0.6 + 0.4 * Math.sin(frame / 3.1 + i * 1.9)))));

  const palabra = Math.max(fade(t, T.palabraIn, T.palabraOut, 0.5), fade(t, T.palabraFinalIn, T.palabraFinalOut, 0.5));

  return (
    <AbsoluteFill style={{ background: "#fff" }}>
      {/* Aro de puntos */}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {puntos.map((d, i) => (
          <circle key={i} cx={d.x} cy={d.y} r={(5.5 + 2.5 * d.k) * d.s} fill={interpolateColors(d.k, [0, 1], [C.line2, C.accent])} />
        ))}
      </svg>
      <div style={{ position: "absolute", left: CX - 115, top: CY - 115, transform: `scale(${logoS})` }}>
        <Isotipo size={230} barras={barras} />
      </div>
      <div style={{ position: "absolute", left: CX - 300, width: 600, top: CY + R + 46, textAlign: "center", opacity: palabra, fontFamily: F.display, fontWeight: 800, fontSize: 76, letterSpacing: "-0.02em", color: C.ink }}>
        Atentina
      </div>

      <Titulo t={t} />
      {CLIENTES.map((_, i) => <Fila key={i} i={i} t={t} pop={pop} />)}
      <Operadora t={t} pop={pop} />
      <Contador t={t} />

      {/* Paquetes arriba de todo */}
      {paquetes.map(({ p, q }) => (q ? <Chip key={p.i} p={q} canal={CLIENTES[p.fila].canal} s={Math.min(1, pop(p.dep) + 0.2)} /> : null))}
    </AbsoluteFill>
  );
};

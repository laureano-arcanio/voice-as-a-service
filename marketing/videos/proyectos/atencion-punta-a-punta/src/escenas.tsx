import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Eyebrow, Icon, Wave, useIn, usePop } from "../../../src/comun/ui";
import { Avatar, Glyph, Nota, PlanBadge, type Retrato, useT, win } from "./piezas";
import { AT, DUR } from "./timeline";

// ---------- piezas del diagrama ----------

type Pt = { x: number; y: number };
const q = (t: number, a: Pt, c: Pt, b: Pt): Pt => ({
  x: (1 - t) ** 2 * a.x + 2 * (1 - t) * t * c.x + t ** 2 * b.x,
  y: (1 - t) ** 2 * a.y + 2 * (1 - t) * t * c.y + t ** 2 * b.y,
});
type Curva = { a: Pt; c: Pt; b: Pt };
const path = ({ a, c, b }: Curva) => `M ${a.x} ${a.y} Q ${c.x} ${c.y} ${b.x} ${b.y}`;

// Nodos: Tomás (cliente) a la izquierda, el agente al centro, el sistema y el equipo a la derecha
const TOM = { x: 270, y: 560 };
const AG = { x: 830, y: 560 };
const RX = 1230; // borde izquierdo de las tarjetas de la derecha
const L_TA: Curva = { a: { x: 385, y: 560 }, c: { x: 530, y: 560 }, b: { x: 680, y: 560 } };
const L_AS: Curva = { a: { x: 965, y: 495 }, c: { x: 1110, y: 390 }, b: { x: RX, y: 395 } };
const L_AV: Curva = { a: { x: 975, y: 590 }, c: { x: 1110, y: 670 }, b: { x: RX, y: 670 } };
const L_AL: Curva = { a: { x: 960, y: 650 }, c: { x: 1080, y: 830 }, b: { x: RX, y: 830 } };

/** Paquete que viaja por una curva entre a y b (s); `back` lo hace ir de b a a. */
const Paquete: React.FC<{ t: number; curva: Curva; a: number; b: number; back?: boolean; color?: string; children: React.ReactNode }> = ({
  t, curva, a, b, back, color = C.accent, children,
}) => {
  if (t < a - 0.1 || t > b + 0.25) return null;
  const k = interpolate(t, [a, b], [0, 1], { ...CLAMP, easing: EASE });
  const p = q(back ? 1 - k : k, curva.a, curva.c, curva.b);
  const o = Math.min(interpolate(t, [a - 0.1, a + 0.05], [0, 1], CLAMP), interpolate(t, [b, b + 0.25], [1, 0], CLAMP));
  return (
    <div style={{
      position: "absolute", left: p.x, top: p.y, transform: "translate(-50%, -50%)", opacity: o, background: color, color: "#fff",
      borderRadius: 999, padding: "8px 16px", fontFamily: F.mono, fontSize: 24, fontWeight: 500, display: "flex", alignItems: "center",
      gap: 8, boxShadow: "0 8px 20px rgba(36,86,230,0.35)", whiteSpace: "nowrap",
    }}>
      {children}
    </div>
  );
};

/** Globo de diálogo que crece hacia arriba desde `bottom` (px desde el borde de abajo). */
const Globo: React.FC<{ t: number; a: number; b: number; left: number; bottom: number; quien: string; agente?: boolean; children: React.ReactNode }> = ({
  t, a, b, left, bottom, quien, agente, children,
}) => {
  const p = win(t, a, b, 0.3);
  if (p <= 0) return null;
  return (
    <div style={{ position: "absolute", left, bottom, opacity: p, transform: `translateY(${(1 - p) * 14}px)`, maxWidth: 560 }}>
      <div style={{
        background: agente ? C.accentSoft : "#fff", border: `2px solid ${agente ? "#c9d6fb" : C.line}`, borderRadius: 24, padding: "12px 22px",
        boxShadow: shadowCard,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.06em", color: agente ? C.accent : C.muted, textTransform: "uppercase" }}>{quien}</div>
        <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 28, color: C.ink, lineHeight: 1.25, marginTop: 2 }}>{children}</div>
      </div>
      <svg width={30} height={18} style={{ position: "absolute", left: 40, bottom: -16 }}>
        <path d="M0 0 L30 0 L4 18 Z" fill={agente ? C.accentSoft : "#fff"} />
        <path d="M0 1 L4 18 L30 1" fill="none" stroke={agente ? "#c9d6fb" : C.line} strokeWidth={2} />
      </svg>
    </div>
  );
};

type Tono = "neutro" | "accent" | "ok" | "warn" | "gris";
const TONOS: Record<Tono, { bg: string; fg: string; bd: string }> = {
  neutro: { bg: "#fff", fg: C.ink2, bd: C.line },
  accent: { bg: C.accentSoft, fg: C.accent2, bd: "#c9d6fb" },
  ok: { bg: C.okSoft, fg: "#11734a", bd: "#b6e6cb" },
  warn: { bg: C.warnSoft, fg: C.warn, bd: "#f6cdc9" },
  gris: { bg: C.surface2, fg: C.muted, bd: C.line },
};
type Estado = { at: number; label: string; icon?: React.ReactNode; tono: Tono };

/** El estado vigente de una lista (el último que ya empezó), con un fundido al cambiar. */
const actual = (t: number, estados: Estado[]) => {
  let cur: Estado | null = null;
  for (const e of estados) if (t >= e.at) cur = e;
  return cur;
};
const EstadoPill: React.FC<{ t: number; estados: Estado[]; size?: number }> = ({ t, estados, size = 24 }) => {
  const e = actual(t, estados);
  if (!e) return null;
  const tn = TONOS[e.tono];
  const p = interpolate(t, [e.at, e.at + 0.25], [0.6, 1], CLAMP);
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 10, background: tn.bg, color: tn.fg, border: `2px solid ${tn.bd}`, borderRadius: 999,
      padding: "6px 16px", fontFamily: F.body, fontWeight: 700, fontSize: size, whiteSpace: "nowrap", opacity: p, transform: `scale(${0.94 + 0.06 * p})`,
    }}>
      {e.icon}
      {e.label}
    </div>
  );
};

/** Aro de puntos del agente (como en landing-agente): un tramo en el acento gira mientras atiende. */
const Aro: React.FC<{ t: number; r: number; on: number }> = ({ t, r, on }) => {
  const n = 40;
  const head = (t * 9) % n;
  return (
    <svg width={r * 2 + 30} height={r * 2 + 30} style={{ position: "absolute", left: AG.x - r - 15, top: AG.y - r - 15, overflow: "visible" }}>
      {Array.from({ length: n }).map((_, i) => {
        const ang = (i / n) * Math.PI * 2 - Math.PI / 2;
        const d = (head - i + n) % n;
        const lit = on * Math.max(0, 1 - d / 9);
        return (
          <circle key={i} cx={r + 15 + r * Math.cos(ang)} cy={r + 15 + r * Math.sin(ang)} r={5 + 2 * lit}
            fill={lit > 0.05 ? C.accent : C.line2} opacity={0.55 + 0.45 * lit} />
        );
      })}
    </svg>
  );
};

/** Tarjeta de una persona del equipo: retrato, orden, área y estado. */
const Operario: React.FC<{ t: number; top: number; id: Retrato; nombre: string; orden: number; p: number; estados: Estado[] }> = ({
  t, top, id, nombre, orden, p, estados,
}) => {
  const e = actual(t, estados);
  const sonando = e?.label === "Sonando";
  const pulso = sonando ? 0.5 + 0.5 * Math.abs(Math.sin(t * 7)) : 0;
  const borde = e?.tono === "ok" ? "#7fd3a6" : sonando ? C.accent : C.line;
  return (
    <div style={{
      position: "absolute", left: RX, top, width: 560, height: 140, background: "#fff", borderRadius: 26, border: `3px solid ${borde}`,
      boxShadow: sonando ? `0 0 0 ${6 + 6 * pulso}px rgba(36,86,230,${0.12 + 0.1 * pulso})` : shadowCard, display: "flex", alignItems: "center",
      gap: 22, padding: "0 24px", opacity: p, transform: `translateX(${(1 - p) * 40}px)`,
    }}>
      <div style={{ position: "relative" }}>
        <Avatar id={id} size={100} gray={e?.label === "No atiende" ? 0.7 : 0} />
        <div style={{
          position: "absolute", right: -6, top: -6, width: 38, height: 38, borderRadius: "50%", background: C.ink, color: "#fff",
          fontFamily: F.mono, fontSize: 20, display: "flex", alignItems: "center", justifyContent: "center", border: "3px solid #fff",
        }}>{orden}</div>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink, lineHeight: 1 }}>{nombre}</div>
        <div style={{ marginTop: 10 }}><EstadoPill t={t} estados={estados} size={22} /></div>
      </div>
    </div>
  );
};

/** Título que cambia con cada momento del diagrama. */
type Beat = { at: number; eyebrow: string; text: string; accent: string };
const Titulos: React.FC<{ t: number; beats: Beat[] }> = ({ t, beats }) => (
  <>
    {beats.map((b, i) => {
      // Sin superponerse: el anterior se va antes de que entre el siguiente
      const fin = i + 1 < beats.length ? beats[i + 1].at - 0.45 : 999;
      const p = win(t, b.at - 0.1, fin, 0.3);
      if (p <= 0) return null;
      return (
        <div key={i} style={{ position: "absolute", left: 120, top: 70, right: 120, opacity: p, transform: `translateY(${(1 - p) * 16}px)` }}>
          <Eyebrow>{b.eyebrow}</Eyebrow>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, lineHeight: 1.08, color: C.ink, marginTop: 12, letterSpacing: "-0.015em" }}>
            {b.text} <span style={{ color: C.accent }}>{b.accent}</span>
          </div>
        </div>
      );
    })}
  </>
);

const Fila: React.FC<{ p: number; tag: string; tagTone: Tono; children: React.ReactNode }> = ({ p, tag, tagTone, children }) => (
  <div style={{
    display: "flex", alignItems: "center", gap: 14, opacity: p, transform: `translateY(${(1 - p) * 10}px)`, fontFamily: F.body, fontWeight: 600,
    fontSize: 25, color: C.ink, borderTop: `1.5px solid ${C.line}`, padding: "11px 0",
  }}>
    <span style={{ color: C.ok, display: "flex" }}><Icon name="check" size={26} color={C.ok} /></span>
    <span style={{ flex: 1, whiteSpace: "nowrap" }}>{children}</span>
    <span style={{
      fontFamily: F.mono, fontSize: 16, letterSpacing: "0.06em", textTransform: "uppercase", background: TONOS[tagTone].bg,
      color: TONOS[tagTone].fg, borderRadius: 8, padding: "3px 10px",
    }}>{tag}</span>
  </div>
);

// ---------- 0. intro ----------

export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.35, 0.7);
  const a1 = usePop(1.3);
  const a2 = usePop(1.7);
  const a3 = usePop(2.1);
  const l = useIn(1.5, 0.8);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 340 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 262, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accent, opacity: useIn(0.2, 0.5) }}>
        ATENCIÓN DE PUNTA A PUNTA
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 320, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 84,
        lineHeight: 1.08, color: C.ink, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Tu cliente llama, el agente resuelve<br /><span style={{ color: C.accent }}>y tu equipo suma cuando hace falta.</span>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d="M 760 700 L 900 700" stroke={C.accent} strokeWidth={4} strokeDasharray="3 12" strokeLinecap="round" opacity={l} />
        <path d="M 1020 700 L 1160 700" stroke={C.accent} strokeWidth={4} strokeDasharray="3 12" strokeLinecap="round" opacity={l} />
      </svg>
      <div style={{ position: "absolute", left: 620, top: 630, transform: `scale(${a1})` }}><Avatar id="tomas" size={140} /></div>
      <div style={{ position: "absolute", left: 890, top: 630, transform: `scale(${a2})` }}><AgenteLogo size={140} /></div>
      <div style={{ position: "absolute", left: 1160, top: 630, transform: `scale(${a3})`, display: "flex" }}>
        <Avatar id="valentina" size={140} />
        <Avatar id="lucas" size={140} style={{ marginLeft: -40 }} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- 1. el diagrama: cliente, agente, sistema y equipo ----------

export const Diagrama: React.FC = () => {
  const t = useT();
  const [t2, t3, t4, t5, t6, t7, t8] = [AT.d2, AT.d3, AT.d4, AT.d5, AT.d6, AT.d7, AT.d8];

  const pTom = usePop(0.1);
  const pAg = usePop(0.35);
  const pSis = usePop(t3 - 0.1);
  const pEqH = useIn(t4 + 0.9, 0.5);
  const pVal = usePop(t4 + 1.3);
  const pLuc = usePop(t4 + 1.6);
  const horario = win(t, t4 + 3.3, t4 + DUR.d4 + 0.4, 0.3);

  // Registro final: el diagrama queda detrás y entra la conversación registrada
  const reg = useIn(t8 + 0.1, 0.6);
  const pReg = usePop(t8 + 0.3);

  const conectados = win(t, t6 + 3.2, t7 + 0.1, 0.3);
  const musica = win(t, t5 + 0.1, t6 + 3.2, 0.3);
  const sisChico = interpolate(t, [t4 + 0.2, t4 + 0.7], [0, 1], { ...CLAMP, easing: EASE });
  const aviso = win(t, t6 + 0.5, t7 + 0.1, 0.35);
  const tecla = usePop(t6 + 2.6);

  // El agente "habla" mientras su globo está a la vista
  const hablaAgente = Math.max(win(t, t4 + 1.4, t4 + 3.2), win(t, t7 + 1.8, t7 + 3.6), win(t, t6 + 0.5, t6 + 2.4)) * 0.8;

  const beats: Beat[] = [
    { at: 0, eyebrow: "1 · Atiende", text: "Tu cliente llama y el agente atiende,", accent: "a cualquier hora." },
    { at: t3, eyebrow: "2 · Consulta y registra", text: "Usa tu sistema", accent: "durante la llamada." },
    { at: t4, eyebrow: "3 · Deriva a tu equipo", text: "Llama a tu gente,", accent: "en tu orden y tu horario." },
    { at: t5, eyebrow: "3 · Deriva a tu equipo", text: "Tu cliente espera con música", accent: "y suena el siguiente." },
    { at: t6, eyebrow: "3 · Deriva a tu equipo", text: "Le cuenta de qué se trata", accent: "y los conecta." },
    { at: t7, eyebrow: "Si nadie atiende", text: "El agente vuelve", accent: "y toma el mensaje." },
    { at: t8, eyebrow: "4 · Queda registrado", text: "Cada conversación,", accent: "de punta a punta." },
  ];

  const estTom: Estado[] = [
    { at: t2 + 0.1, label: "Llamando", icon: <Glyph name="ring" size={22} />, tono: "accent" },
    { at: t2 + 1.1, label: "En llamada", icon: <Icon name="phone" size={22} />, tono: "ok" },
    { at: t5 + 0.1, label: "Música de espera", icon: <Glyph name="music" size={22} />, tono: "accent" },
    { at: t6 + 3.2, label: "Hablando con Lucas", icon: <Icon name="phone" size={22} />, tono: "ok" },
    { at: t7 + 0.1, label: "En espera", icon: <Glyph name="music" size={22} />, tono: "accent" },
    { at: t7 + 1.8, label: "Deja su mensaje", icon: <Glyph name="doc" size={22} />, tono: "ok" },
  ];
  const noAt = { label: "No atiende", icon: <Glyph name="x" size={20} />, tono: "gris" as Tono };
  const sonando = { label: "Sonando", icon: <Glyph name="ring" size={20} />, tono: "accent" as Tono };
  const enEspera = { label: "Disponible", tono: "neutro" as Tono };
  const estVal: Estado[] = [{ at: 0, ...enEspera }, { at: t5 + 1.5, ...sonando }, { at: t5 + 2.6, ...noAt }];
  const estLuc: Estado[] = [
    { at: 0, ...enEspera }, { at: t5 + 3.5, ...sonando },
    { at: t6 + 0.1, label: "Atendió", icon: <Icon name="phone" size={20} />, tono: "accent" },
    { at: t6 + 3.2, label: "Conectado con Tomás", icon: <Icon name="check" size={20} />, tono: "ok" },
    { at: t7 + 0.4, ...noAt },
  ];

  // Con el sistema achicado a un chip, la línea termina en el chip
  const lAS: Curva = { ...L_AS, b: { x: RX, y: 395 - 70 * sisChico }, c: { x: 1110, y: 390 - 60 * sisChico } };
  const verde = (base: string) => (conectados > 0.5 ? C.ok : base);

  return (
    <AbsoluteFill>
      <Titulos t={t} beats={beats} />

      <AbsoluteFill style={{ opacity: 1 - 0.93 * reg, transform: `scale(${1 - 0.05 * reg})` }}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          <path d={path(L_TA)} stroke={verde(C.accent)} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={pAg * 0.8} />
          <path d={path(lAS)} stroke={C.accent} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={pSis * 0.8} />
          <path d={path(L_AV)} stroke={C.accent} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={pVal * 0.7} />
          <path d={path(L_AL)} stroke={verde(C.accent)} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={pLuc * 0.7} />
        </svg>

        {/* Tomás, el cliente */}
        <div style={{ position: "absolute", left: TOM.x - 100, top: TOM.y - 100, transform: `scale(${pTom})` }}>
          <Avatar id="tomas" size={200} ring={conectados > 0.5 ? "#9ee0bb" : undefined} />
          {musica > 0 ? [0, 1, 2].map((i) => {
            const k = ((t * 0.6 + i / 3) % 1);
            return (
              <div key={i} style={{ position: "absolute", left: 170 + i * 16, top: 40 - k * 90, opacity: musica * Math.sin(k * Math.PI), color: C.accent }}>
                <Glyph name="music" size={30} color={C.accent} />
              </div>
            );
          }) : null}
        </div>
        <div style={{ position: "absolute", left: TOM.x - 200, width: 400, top: TOM.y + 116, textAlign: "center", opacity: pTom }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ink, lineHeight: 1 }}>Tomás</div>
          <Nota style={{ marginTop: 6, fontSize: 19, letterSpacing: "0.08em" }}>TU CLIENTE</Nota>
          <div style={{ marginTop: 14 }}><EstadoPill t={t} estados={estTom} /></div>
        </div>

        {/* El agente: el logo con el aro y la voz elegida */}
        <Aro t={t} r={138} on={pAg} />
        <div style={{ position: "absolute", left: AG.x - 105, top: AG.y - 105, transform: `scale(${pAg})` }}>
          <AgenteLogo size={210} talk={hablaAgente} />
        </div>
        <div style={{ position: "absolute", left: AG.x - 200, width: 400, top: AG.y + 158, textAlign: "center", opacity: pAg }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ink, lineHeight: 1 }}>Tu agente</div>
          <div style={{ marginTop: 12, display: "inline-flex", alignItems: "center", gap: 10, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 999, padding: "4px 16px 4px 5px" }}>
            <Avatar id="sofia" size={38} />
            <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 21, color: C.ink2 }}>con la voz de Sofía</span>
          </div>
        </div>

        {/* Tu sistema: grande mientras consulta, después queda como un chip */}
        <div style={{
          position: "absolute", left: RX, top: 268, width: 560, opacity: pSis * (1 - sisChico), transform: `translateX(${(1 - pSis) * 40}px)`,
          background: "#fff", borderRadius: 26, border: `2px solid ${C.line}`, boxShadow: shadowCard, padding: "18px 26px 8px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <Glyph name="db" size={32} color={C.accent} />
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Tu sistema</span>
            <Nota style={{ marginLeft: "auto" }}>agenda · CRM · gestión</Nota>
          </div>
          <Fila p={win(t, t3 + 1.0)} tag="consulta" tagTone="accent">Cliente: Tomás Ríos</Fila>
          <Fila p={win(t, t3 + 1.7)} tag="consulta" tagTone="accent">Pedido 4821: sale mañana</Fila>
          <Fila p={win(t, t3 + 3.4)} tag="registra" tagTone="ok">Suma 10 unidades</Fila>
        </div>
        <div style={{
          position: "absolute", left: RX, top: 300, opacity: pSis * sisChico, display: "inline-flex", alignItems: "center", gap: 12,
          background: "#fff", borderRadius: 999, border: `2px solid ${C.line}`, boxShadow: shadowCard, padding: "10px 22px",
        }}>
          <Glyph name="db" size={28} color={C.accent} />
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 25, color: C.ink }}>Tu sistema</span>
          <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 22, color: C.ok }}>pedido actualizado</span>
          <Icon name="check" size={24} color={C.ok} />
        </div>

        {/* Tu equipo: Ventas, con su horario y las personas en orden */}
        <div style={{ position: "absolute", left: RX, top: 548, width: 560, display: "flex", alignItems: "center", gap: 14, opacity: pEqH }}>
          <Icon name="users" size={30} color={C.accent} />
          <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Tu equipo · Ventas</span>
          <div style={{
            marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: 8, borderRadius: 999, padding: "4px 14px",
            background: horario > 0.5 ? C.accentSoft : "#fff", border: `2px solid ${horario > 0.5 ? C.accent : C.line}`, color: horario > 0.5 ? C.accent2 : C.ink2,
            fontFamily: F.body, fontWeight: 700, fontSize: 20, whiteSpace: "nowrap",
          }}>
            <Icon name="clock" size={20} />Lun a vie, 9 a 18
          </div>
        </div>
        <Operario t={t} top={600} id="valentina" nombre="Valentina" orden={1} p={pVal} estados={estVal} />
        <Operario t={t} top={760} id="lucas" nombre="Lucas" orden={2} p={pLuc} estados={estLuc} />

        {/* Aviso solo a Lucas (el cliente no lo escucha) */}
        {aviso > 0 ? (
          <div style={{
            position: "absolute", left: RX, top: 372, width: 560, opacity: aviso, transform: `translateY(${(1 - aviso) * 12}px)`,
            background: C.ink, color: C.ctaInk, borderRadius: 22, padding: "14px 22px", boxShadow: shadowCard,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Avatar id="lucas" size={34} />
              <span style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.06em", color: C.accentOnDark }}>EL AGENTE A LUCAS · TOMÁS NO LO ESCUCHA</span>
            </div>
            <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 24, lineHeight: 1.3, marginTop: 8, display: "flex", alignItems: "flex-end", gap: 14 }}>
              <span style={{ flex: 1 }}>Derivación de Ventas: Tomás quiere sumar 10 unidades. Marcá 1 para atender.</span>
              <div style={{ transform: `scale(${tecla})`, display: "flex", alignItems: "center", justifyContent: "center", width: 52, height: 52, borderRadius: 14, background: C.accent, fontFamily: F.mono, fontSize: 28, color: "#fff", flexShrink: 0 }}>1</div>
            </div>
          </div>
        ) : null}

        {/* Conectados */}
        <div style={{
          position: "absolute", left: AG.x - 230, width: 460, top: 900, display: "flex", justifyContent: "center", opacity: conectados,
          transform: `scale(${0.9 + 0.1 * conectados})`,
        }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 10, background: C.okSoft, color: "#11734a", border: "2px solid #b6e6cb", borderRadius: 999, padding: "8px 20px", fontFamily: F.body, fontWeight: 700, fontSize: 24 }}>
            <Icon name="check" size={24} color={C.ok} />Tomás y Lucas, conectados
          </div>
        </div>
        {conectados > 0 ? (
          <div style={{ position: "absolute", left: 560, top: 520, opacity: conectados }}><Wave n={6} h={30} color={C.ok} /></div>
        ) : null}

        {/* Paquetes */}
        <Paquete t={t} curva={L_TA} a={t2 + 0.2} b={t2 + 1.1}><Wave n={5} h={22} /></Paquete>
        <Paquete t={t} curva={lAS} a={t3 + 0.3} b={t3 + 1.0}>{"{ }"}</Paquete>
        <Paquete t={t} curva={lAS} a={t3 + 1.9} b={t3 + 2.6} back color={C.ok}><Icon name="check" size={22} color="#fff" /></Paquete>
        <Paquete t={t} curva={lAS} a={t3 + 2.9} b={t3 + 3.4}>{"{ }"}</Paquete>
        <Paquete t={t} curva={L_AV} a={t5 + 1.0} b={t5 + 1.5}><Glyph name="ring" size={22} color="#fff" /></Paquete>
        <Paquete t={t} curva={L_AL} a={t5 + 3.0} b={t5 + 3.5}><Glyph name="ring" size={22} color="#fff" /></Paquete>
        <Paquete t={t} curva={L_AL} a={t6 + 0.2} b={t6 + 0.8}>Aa</Paquete>
        <Paquete t={t} curva={L_AL} a={t7 + 0.8} b={t7 + 1.4} back color={C.muted}><Glyph name="x" size={22} color="#fff" /></Paquete>
        <Paquete t={t} curva={L_TA} a={t7 + 1.4} b={t7 + 2.1} back><Wave n={5} h={22} /></Paquete>

        {/* Globos (ilustrativos) */}
        <Globo t={t} a={t2 + 0.3} b={t3 + 0.6} left={130} bottom={1080 - 430} quien="Tomás">¿Cómo viene mi pedido?</Globo>
        <Globo t={t} a={t3 + 2.3} b={t4 - 0.1} left={130} bottom={1080 - 430} quien="Tomás">Y quiero sumar diez unidades.</Globo>
        <Globo t={t} a={t4 + 0.2} b={t5 - 0.2} left={130} bottom={1080 - 430} quien="Tomás">¿Me pasás con Ventas?</Globo>
        <Globo t={t} a={t4 + 1.4} b={t5 + 0.3} left={690} bottom={1080 - 400} quien="Agente" agente>Te paso con Ventas, un momento.</Globo>
        <Globo t={t} a={t7 + 1.8} b={t8 + 0.1} left={420} bottom={1080 - 400} quien="Agente" agente>No pude comunicarte con Ventas.<br />¿Te tomo el mensaje?</Globo>
      </AbsoluteFill>

      {/* Lo que queda registrado */}
      {reg > 0 ? <Registro t={t} p={pReg} t8={t8} /> : null}
    </AbsoluteFill>
  );
};

const Columna: React.FC<{ p: number; titulo: string; icon: React.ReactNode; children: React.ReactNode }> = ({ p, titulo, icon, children }) => (
  <div style={{ flex: 1, opacity: p, transform: `translateY(${(1 - p) * 18}px)`, background: C.bg2, borderRadius: 20, padding: "20px 24px", border: `2px solid ${C.line}` }}>
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
      {icon}
      <span style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent, textTransform: "uppercase" }}>{titulo}</span>
    </div>
    {children}
  </div>
);

const Linea: React.FC<{ quien: string; children: React.ReactNode; color?: string }> = ({ quien, children, color = C.ink2 }) => (
  <div style={{ fontFamily: F.body, fontSize: 22, lineHeight: 1.3, color: C.ink, marginBottom: 10 }}>
    <span style={{ fontWeight: 700, color }}>{quien}: </span>{children}
  </div>
);

const Dato: React.FC<{ k: string; v: string }> = ({ k, v }) => (
  <div style={{ marginBottom: 12 }}>
    <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted, letterSpacing: "0.04em" }}>{k}</div>
    <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 25, color: C.ink }}>{v}</div>
  </div>
);

const Registro: React.FC<{ t: number; p: number; t8: number }> = ({ t, p, t8 }) => (
  <div style={{
    position: "absolute", left: 200, top: 250, width: 1520, background: "#fff", borderRadius: 30, border: `2px solid ${C.line}`,
    boxShadow: "0 24px 60px rgba(11,18,32,0.14)", padding: "26px 32px", transform: `scale(${0.9 + 0.1 * p})`, opacity: Math.min(1, p * 1.4),
  }}>
    <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
      <Avatar id="tomas" size={60} />
      <div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink, lineHeight: 1 }}>Conversación con Tomás Ríos</div>
        <Nota style={{ marginTop: 6 }}>Teléfono · hoy 10:42 · 3:12 min</Nota>
      </div>
      <Nota style={{ marginLeft: "auto" }}>datos ilustrativos</Nota>
    </div>
    <div style={{ display: "flex", gap: 22 }}>
      <Columna p={win(t, t8 + 1.9)} titulo="Conversación" icon={<Glyph name="doc" size={26} color={C.accent} />}>
        <Linea quien="Tomás">¿Cómo viene mi pedido?</Linea>
        <Linea quien="Agente" color={C.accent}>Sale mañana. ¿Algo más?</Linea>
        <Linea quien="Lucas (equipo)" color={C.ok}>Te armo el precio.</Linea>
      </Columna>
      <Columna p={win(t, t8 + 2.9)} titulo="Datos" icon={<Glyph name="db" size={26} color={C.accent} />}>
        <Dato k="Cliente" v="Tomás Ríos" />
        <Dato k="Pedido" v="4821 · suma 10 unidades" />
      </Columna>
      <Columna p={win(t, t8 + 3.7)} titulo="Resultado" icon={<Icon name="check" size={26} color={C.accent} />}>
        <Dato k="Derivada a" v="Ventas · atendió Lucas" />
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: C.okSoft, color: "#11734a", borderRadius: 999, padding: "6px 16px", fontFamily: F.body, fontWeight: 700, fontSize: 22 }}>
          <Icon name="check" size={22} color={C.ok} />Resuelta
        </div>
      </Columna>
    </div>
  </div>
);

// ---------- 2. lo que se puede hacer y configurar ----------

const ITEMS = [
  "Atiende las 24 horas",
  "Por teléfono, WhatsApp y la web",
  "Voces argentinas: elegís la tuya",
  "Consulta y registra en tu sistema",
  "Deriva a tu equipo, en tu orden y horario",
  "Música de espera y aviso a quien atiende",
  "Si nadie atiende, toma el mensaje",
  "Varias llamadas a la vez",
  "Transcripción, datos y resultado de cada una",
  "Reportes de consultas y derivaciones",
];

export const Checklist: React.FC = () => {
  const t = useT();
  const head = useIn(0.1, 0.6);
  const ticks = ITEMS.map((_, i) => usePop(0.5 + i * 0.5));
  const plan = useIn(5.8, 0.5);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 120, top: 70, right: 120, opacity: head, transform: `translateY(${(1 - head) * 16}px)` }}>
        <Eyebrow>Lo que hace · lo que configurás</Eyebrow>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, lineHeight: 1.08, color: C.ink, marginTop: 12, letterSpacing: "-0.015em" }}>
          Todo esto, <span style={{ color: C.accent }}>a la medida de tu empresa.</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 140, top: 270, width: 1640, display: "grid", gridTemplateColumns: "1fr 1fr", gridAutoFlow: "column", gridTemplateRows: "repeat(5, 112px)", columnGap: 40 }}>
        {ITEMS.map((txt, i) => {
          const p = ticks[i];
          const on = t > 0.5 + i * 0.5;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 22, opacity: Math.min(1, p * 1.5), transform: `translateX(${(1 - p) * 24}px)` }}>
              <div style={{
                width: 60, height: 60, borderRadius: 18, background: on ? C.accent : "#fff", border: `3px solid ${on ? C.accent : C.line2}`,
                display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${0.7 + 0.3 * p})`, flexShrink: 0,
              }}>
                <Icon name="check" size={40} color="#fff" />
              </div>
              <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 36, color: C.ink, whiteSpace: "nowrap" }}>{txt}</span>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 140, top: 862 }}>
        <PlanBadge p={plan}>Telefonía, WhatsApp, herramientas, equipo y llamadas a la vez, según el plan</PlanBadge>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 3. cierre ----------

export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const title = useIn(0.4, 0.7);
  const url = useIn(1.6, 0.6);
  const tel = useIn(2.2, 0.6);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 200, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 420 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 86,
        lineHeight: 1.08, color: C.ink, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Agentes con IA que atienden<br /><span style={{ color: C.accent }}>a tus clientes.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 640, display: "flex", justifyContent: "center", opacity: url, transform: `translateY(${(1 - url) * 14}px)` }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 999, padding: "16px 40px", fontFamily: F.mono, fontSize: 40 }}>atentina.com.ar</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 750, textAlign: "center", fontFamily: F.body, fontWeight: 600, fontSize: 30, color: C.muted, opacity: tel }}>
        o llamá al 0800-220-1233 y hablá con nuestro agente
      </div>
    </AbsoluteFill>
  );
};

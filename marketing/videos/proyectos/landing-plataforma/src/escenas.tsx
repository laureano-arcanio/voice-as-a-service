import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Eyebrow, Icon, Wave, useIn, usePop } from "../../../src/comun/ui";
import { Avatar, Glyph, Nota, PlanBadge, type Retrato, useT, win } from "./piezas";
import { AT } from "./timeline";

// ---------- piezas del diagrama (copiadas de atencion-punta-a-punta) ----------

type Pt = { x: number; y: number };
const q = (t: number, a: Pt, c: Pt, b: Pt): Pt => ({
  x: (1 - t) ** 2 * a.x + 2 * (1 - t) * t * c.x + t ** 2 * b.x,
  y: (1 - t) ** 2 * a.y + 2 * (1 - t) * t * c.y + t ** 2 * b.y,
});
type Curva = { a: Pt; c: Pt; b: Pt };
const path = ({ a, c, b }: Curva) => `M ${a.x} ${a.y} Q ${c.x} ${c.y} ${b.x} ${b.y}`;

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

const Linea: React.FC<{ curva: Curva; p: number; color?: string }> = ({ curva, p, color = C.accent }) => (
  <path d={path(curva)} stroke={color} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={p * 0.75} />
);

/** Aro de puntos del agente (como en landing-agente): un tramo en el acento gira mientras atiende. */
const Aro: React.FC<{ t: number; cx: number; cy: number; r: number; on: number }> = ({ t, cx, cy, r, on }) => {
  const n = 40;
  const head = (t * 9) % n;
  return (
    <svg width={r * 2 + 30} height={r * 2 + 30} style={{ position: "absolute", left: cx - r - 15, top: cy - r - 15, overflow: "visible", opacity: on }}>
      {Array.from({ length: n }).map((_, i) => {
        const ang = (i / n) * Math.PI * 2 - Math.PI / 2;
        const d = (head - i + n) % n;
        const lit = Math.max(0, 1 - d / 9);
        return (
          <circle key={i} cx={r + 15 + r * Math.cos(ang)} cy={r + 15 + r * Math.sin(ang)} r={5 + 2 * lit}
            fill={lit > 0.05 ? C.accent : C.line2} opacity={0.55 + 0.45 * lit} />
        );
      })}
    </svg>
  );
};

/** El agente: el logo con el aro, siempre en el mismo lugar. */
const Agente: React.FC<{ t: number; cx: number; cy: number; size: number; p: number; talk?: number }> = ({ t, cx, cy, size, p, talk = 0 }) => (
  <>
    <Aro t={t} cx={cx} cy={cy} r={size * 0.66} on={p} />
    <div style={{ position: "absolute", left: cx - size / 2, top: cy - size / 2, transform: `scale(${p})` }}>
      <AgenteLogo size={size} talk={talk} />
    </div>
  </>
);

/** Título que cambia con cada momento de la escena. */
type Beat = { at: number; eyebrow: string; text: string; accent: string };
const Titulos: React.FC<{ t: number; beats: Beat[] }> = ({ t, beats }) => (
  <>
    {beats.map((b, i) => {
      // Sin superponerse: el anterior se va antes de que entre el siguiente
      const fin = i + 1 < beats.length ? beats[i + 1].at - 0.45 : 999;
      const p = win(t, b.at - 0.1, fin, 0.3);
      if (p <= 0) return null;
      return (
        <div key={i} style={{ position: "absolute", left: 120, top: 64, right: 120, opacity: p, transform: `translateY(${(1 - p) * 16}px)` }}>
          <Eyebrow>{b.eyebrow}</Eyebrow>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, lineHeight: 1.08, color: C.ink, marginTop: 12, letterSpacing: "-0.015em" }}>
            {b.text} <span style={{ color: C.accent }}>{b.accent}</span>
          </div>
        </div>
      );
    })}
  </>
);

const Check: React.FC<{ on: number; size?: number }> = ({ on, size = 40 }) => (
  <div style={{
    width: size, height: size, borderRadius: size * 0.3, background: on > 0.5 ? C.ok : "#fff", border: `3px solid ${on > 0.5 ? C.ok : C.line2}`,
    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transform: `scale(${0.85 + 0.15 * on})`,
  }}>
    {on > 0.5 ? <Icon name="check" size={size * 0.66} color="#fff" /> : null}
  </div>
);

const Estado: React.FC<{ label: string; tono: "ok" | "accent" | "neutro"; icon?: React.ReactNode; size?: number }> = ({ label, tono, icon, size = 21 }) => {
  const s = tono === "ok" ? { bg: C.okSoft, fg: "#11734a", bd: "#b6e6cb" } : tono === "accent" ? { bg: C.accentSoft, fg: C.accent2, bd: "#c9d6fb" } : { bg: "#fff", fg: C.ink2, bd: C.line };
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 8, background: s.bg, color: s.fg, border: `2px solid ${s.bd}`, borderRadius: 999,
      padding: "3px 12px", fontFamily: F.body, fontWeight: 700, fontSize: size, whiteSpace: "nowrap",
    }}>
      {icon}
      {label}
    </div>
  );
};

// ---------- 0. intro ----------

export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.35, 0.7);
  const cli = [usePop(1.2), usePop(1.35), usePop(1.5)];
  const ag = usePop(1.8);
  const eq = usePop(2.3);
  const l1 = useIn(1.6, 0.6);
  const l2 = useIn(2.1, 0.6);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 130, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 340 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 272, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accent, opacity: useIn(0.2, 0.5) }}>
        LA PLATAFORMA
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 330, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 84,
        lineHeight: 1.08, color: C.ink, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Agentes con IA que atienden<br /><span style={{ color: C.accent }}>a tus clientes.</span>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d="M 812 705 L 912 705" stroke={C.accent} strokeWidth={4} strokeDasharray="3 12" strokeLinecap="round" opacity={l1} />
        <path d="M 1088 705 L 1188 705" stroke={C.accent} strokeWidth={4} strokeDasharray="3 12" strokeLinecap="round" opacity={l2} />
      </svg>
      <div style={{ position: "absolute", left: 510, top: 645, display: "flex" }}>
        {(["tomas", "lucia", "martina"] as Retrato[]).map((id, i) => (
          <div key={id} style={{ marginLeft: i ? -36 : 0, transform: `scale(${cli[i]})` }}><Avatar id={id} size={120} /></div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 925, top: 630, transform: `scale(${ag})` }}><AgenteLogo size={150} /></div>
      <div style={{ position: "absolute", left: 1205, top: 645, display: "flex", transform: `scale(${eq})` }}>
        <Avatar id="valentina" size={120} />
        <Avatar id="lucas" size={120} style={{ marginLeft: -36 }} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- 1. la plataforma: el agente al centro y lo que suma cada línea ----------

const AG = { x: 960, y: 570 };
const RX = 1320; // borde izquierdo de las tarjetas de la derecha

type Cliente = { id: Retrato; nombre: string; canal: string; icon: React.ReactNode; top: number; paquete: React.ReactNode };
const CLIENTES: Cliente[] = [
  { id: "tomas", nombre: "Tomás", canal: "Teléfono", icon: <Icon name="phone" size={20} />, top: 290, paquete: <Wave n={5} h={22} /> },
  { id: "lucia", nombre: "Lucía", canal: "WhatsApp", icon: <Icon name="wa" size={20} />, top: 500, paquete: "Aa" },
  { id: "martina", nombre: "Martina", canal: "Web", icon: <Icon name="web" size={20} />, top: 710, paquete: <Wave n={5} h={22} /> },
];
const CW = 420; // ancho de la tarjeta de un cliente (desde x 110)
const curvaCliente = (top: number): Curva => {
  const cy = top + 60;
  return { a: { x: 110 + CW + 12, y: cy }, c: { x: 700, y: cy }, b: { x: AG.x - 150, y: AG.y + (cy - AG.y) * 0.3 } };
};
const L_SIS: Curva = { a: { x: AG.x + 120, y: AG.y - 90 }, c: { x: 1220, y: 395 }, b: { x: RX - 10, y: 395 } };
const L_OUT: Curva = { a: { x: AG.x + 130, y: AG.y + 60 }, c: { x: 1220, y: 690 }, b: { x: RX - 10, y: 690 } };
const L_EQ: Curva = { a: { x: AG.x, y: AG.y + 125 }, c: { x: AG.x, y: AG.y + 170 }, b: { x: AG.x, y: 795 } };

const TAREAS = [
  { tag: "Turno", txt: "Turno: jueves a las 10", tipo: "registra" },
  { tag: "Consulta", txt: "Consulta: horarios y precios", tipo: "responde" },
  { tag: "Pedido", txt: "Pedido: 2 cajas, envío el lunes", tipo: "registra" },
];
const SALIENTES: { id: Retrato; nombre: string; txt: string }[] = [
  { id: "mariana", nombre: "Mariana", txt: "Confirma su turno" },
  { id: "federico", nombre: "Federico", txt: "Recordatorio de vencimiento" },
  { id: "agustina", nombre: "Agustina", txt: "Campaña de novedades" },
];
const VOCES: { id: Retrato; nombre: string }[] = [
  { id: "sofia", nombre: "Sofía" }, { id: "martin", nombre: "Martín" }, { id: "carolina", nombre: "Carolina" }, { id: "diego", nombre: "Diego" },
  { id: "jimena", nombre: "Jimena" }, { id: "mateo", nombre: "Mateo" }, { id: "gabriela", nombre: "Gabriela" }, { id: "camila", nombre: "Camila" },
];

export const Plataforma: React.FC = () => {
  const t = useT();
  const [t2, t3, t4, t5, t6] = [AT.l2, AT.l3, AT.l4, AT.l5, AT.l6];

  const pAg = usePop(0.05);
  const pCli = [usePop(t2 + 0.3), usePop(t2 + 1.1), usePop(t2 + 2.0)];
  const llega = t2 + 3.5; // los tres paquetes llegan a la vez
  const pHoras = usePop(t2 + 3.7);
  const pSis = usePop(t3 - 0.05);
  const pOut = usePop(t4 - 0.05);
  const pPlan = useIn(t4 + 3.4, 0.4);
  const pEq = usePop(t5 + 0.2);
  // En l6 lo de alrededor se va y entran las voces y el panel
  const lado = 1 - interpolate(t, [t6 - 0.1, t6 + 0.35], [0, 1], CLAMP);
  const pVoces = VOCES.map((_, i) => usePop(t6 + 0.15 + i * 0.1));
  const p41 = useIn(t6 + 0.3, 0.5);
  const pConv = usePop(t6 + 2.3);
  const elegida = t < t6 + 1.0 ? -1 : Math.floor((t - (t6 + 1.0)) / 0.42) % VOCES.length;
  const voz = elegida < 0 ? VOCES[0] : VOCES[elegida];
  const pChip = useIn(t6 + 0.9, 0.3);

  const atendido = t >= llega;
  const derivada = t >= t5 + 2.2;

  const beats: Beat[] = [
    { at: 0, eyebrow: "1 · Atiende", text: "Llamadas, WhatsApp y web,", accent: "a cualquier hora." },
    { at: t3, eyebrow: "2 · Resuelve", text: "Turnos, consultas y pedidos,", accent: "en tu sistema." },
    { at: t4, eyebrow: "3 · Llama", text: "También llama", accent: "a tus clientes." },
    { at: t5, eyebrow: "4 · Deriva", text: "Si hace falta una persona,", accent: "pasa con tu equipo." },
    { at: t6, eyebrow: "5 · Voces y panel", text: "41 voces argentinas,", accent: "todo en tu panel." },
  ];

  return (
    <AbsoluteFill>
      <Titulos t={t} beats={beats} />

      {/* Lo de alrededor del agente: clientes, sistema, salientes y equipo */}
      <AbsoluteFill style={{ opacity: lado }}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          {CLIENTES.map((c, i) => <Linea key={c.id} curva={curvaCliente(c.top)} p={pCli[i]} color={i === 0 && derivada ? C.ok : C.accent} />)}
          <Linea curva={L_SIS} p={pSis} />
          <Linea curva={L_OUT} p={pOut} />
          <Linea curva={L_EQ} p={pEq} color={derivada ? C.ok : C.accent} />
        </svg>

        {/* Clientes, cada uno por su canal */}
        {CLIENTES.map((c, i) => (
          <div key={c.id} style={{
            position: "absolute", left: 110, top: c.top, width: CW, height: 120, background: "#fff", borderRadius: 24,
            border: `2px solid ${i === 0 && derivada ? "#7fd3a6" : C.line}`, boxShadow: shadowCard, display: "flex", alignItems: "center", gap: 18, padding: "0 20px",
            opacity: Math.min(1, pCli[i] * 1.4), transform: `translateX(${(1 - pCli[i]) * -30}px)`,
          }}>
            <div style={{ position: "relative" }}>
              <Avatar id={c.id} size={86} />
              {atendido ? (
                <div style={{ position: "absolute", right: -6, bottom: -4, transform: `scale(${interpolate(t, [llega, llega + 0.25], [0.4, 1], CLAMP)})` }}>
                  <Check on={1} size={34} />
                </div>
              ) : null}
            </div>
            <div>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, lineHeight: 1 }}>{c.nombre}</div>
              <div style={{ marginTop: 10 }}>
                {i === 0 && derivada
                  ? <Estado label="Con Valentina" tono="ok" icon={<Icon name="phone" size={20} />} />
                  : <Estado label={c.canal} tono="accent" icon={c.icon} />}
              </div>
            </div>
          </div>
        ))}

        {/* Tu sistema: las tareas llegan como paquetes y quedan registradas */}
        <div style={{
          position: "absolute", left: RX, top: 268, width: 490, background: "#fff", borderRadius: 24, border: `2px solid ${C.line}`, boxShadow: shadowCard,
          padding: "16px 24px 8px", opacity: Math.min(1, pSis * 1.4), transform: `translateX(${(1 - pSis) * 30}px)`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <Glyph name="db" size={30} color={C.accent} />
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Tu sistema</span>
            <Nota style={{ marginLeft: "auto" }}>agenda · gestión</Nota>
          </div>
          {TAREAS.map((r, i) => {
            const p = win(t, t3 + 0.95 + i * 0.85);
            return (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 12, borderTop: `1.5px solid ${C.line}`, padding: "9px 0", opacity: 0.25 + 0.75 * p,
                fontFamily: F.body, fontWeight: 600, fontSize: 23, color: C.ink,
              }}>
                <Check on={p} size={30} />
                <span style={{ flex: 1, whiteSpace: "nowrap" }}>{r.txt}</span>
              </div>
            );
          })}
        </div>

        {/* Llamadas salientes */}
        <div style={{
          position: "absolute", left: RX, top: 560, width: 490, background: "#fff", borderRadius: 24, border: `2px solid ${C.line}`, boxShadow: shadowCard,
          padding: "16px 24px 8px", opacity: Math.min(1, pOut * 1.4), transform: `translateX(${(1 - pOut) * 30}px)`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <Glyph name="out" size={30} color={C.accent} />
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Llamadas salientes</span>
          </div>
          {SALIENTES.map((r, i) => {
            const p = win(t, t4 + 2.0 + i * 0.75);
            return (
              <div key={r.id} style={{ display: "flex", alignItems: "center", gap: 14, borderTop: `1.5px solid ${C.line}`, padding: "8px 0" }}>
                <Avatar id={r.id} size={50} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, lineHeight: 1.1 }}>{r.nombre}</div>
                  <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 19, color: C.muted, whiteSpace: "nowrap" }}>{r.txt}</div>
                </div>
                <Check on={p} size={34} />
              </div>
            );
          })}
        </div>
        <div style={{ position: "absolute", left: RX, top: 880 }}>
          <PlanBadge p={pPlan}>Llamadas salientes: Sucursal y Red</PlanBadge>
        </div>

        {/* Tu equipo, debajo del agente */}
        <div style={{
          position: "absolute", left: AG.x - 270, top: 795, width: 540, background: "#fff", borderRadius: 24,
          border: `2px solid ${derivada ? "#7fd3a6" : C.line}`, boxShadow: shadowCard, padding: "12px 22px 14px",
          opacity: Math.min(1, pEq * 1.4), transform: `translateY(${(1 - pEq) * 24}px)`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Icon name="users" size={26} color={C.accent} />
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 26, color: C.ink }}>Tu equipo</span>
          </div>
          <div style={{ display: "flex", gap: 18, marginTop: 10 }}>
            {([["valentina", "Valentina"], ["lucas", "Lucas"]] as [Retrato, string][]).map(([id, nombre], i) => (
              <div key={id} style={{ flex: 1, display: "flex", alignItems: "center", gap: 12 }}>
                <Avatar id={id} size={62} ring={i === 0 && derivada ? "#9ee0bb" : undefined} />
                <div>
                  <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, lineHeight: 1.1 }}>{nombre}</div>
                  <div style={{ marginTop: 4 }}>
                    {i === 0 && derivada
                      ? <Estado label="Atendió" tono="ok" icon={<Icon name="phone" size={18} />} size={18} />
                      : <Estado label="Disponible" tono="neutro" size={18} />}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Paquetes */}
        {CLIENTES.map((c) => (
          <Paquete key={c.id} t={t} curva={curvaCliente(c.top)} a={t2 + 2.6} b={llega}>{c.paquete}</Paquete>
        ))}
        {TAREAS.map((r, i) => (
          <Paquete key={r.tag} t={t} curva={L_SIS} a={t3 + 0.3 + i * 0.85} b={t3 + 0.95 + i * 0.85}>{"{ }"} {r.tag}</Paquete>
        ))}
        {SALIENTES.map((r, i) => (
          <Paquete key={r.id} t={t} curva={L_OUT} a={t4 + 1.4 + i * 0.75} b={t4 + 2.0 + i * 0.75}><Glyph name="ring" size={22} color="#fff" /></Paquete>
        ))}
        <Paquete t={t} curva={L_EQ} a={t5 + 1.6} b={t5 + 2.2}><Glyph name="ring" size={22} color="#fff" /></Paquete>
      </AbsoluteFill>

      {/* Encima del agente: quién es y las 24 horas */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 352, display: "flex", justifyContent: "center", alignItems: "center", gap: 16, opacity: pAg * lado }}>
        <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Tu agente</span>
        <div style={{ transform: `scale(${pHoras})` }}>
          <Estado label="Las 24 horas" tono="accent" icon={<Icon name="clock" size={20} />} />
        </div>
      </div>

      {/* El agente, fijo al centro */}
      <Agente t={t} cx={AG.x} cy={AG.y} size={180} p={pAg} talk={win(t, t6 + 1.0, t6 + 4.5) * 0.7} />

      {/* l6: las voces alrededor del agente */}
      {VOCES.map((v, i) => {
        const ang = (i / VOCES.length) * Math.PI * 2 - Math.PI / 2;
        const r = 225;
        const on = i === elegida;
        return (
          <div key={v.id} style={{ position: "absolute", left: AG.x + r * Math.cos(ang) - 44, top: AG.y + r * Math.sin(ang) - 44, transform: `scale(${pVoces[i] * (on ? 1.12 : 1)})` }}>
            <Avatar id={v.id} size={88} ring={on ? C.accent : undefined} />
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: 862, display: "flex", justifyContent: "center", opacity: pChip }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 10, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 999, padding: "4px 18px 4px 5px", boxShadow: shadowCard }}>
          <Avatar id={voz.id} size={40} />
          <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 23, color: C.ink2 }}>con la voz de {voz.nombre}</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 150, top: 390, width: 460, opacity: p41, transform: `translateY(${(1 - p41) * 16}px)` }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 190, color: C.accent, lineHeight: 0.9, letterSpacing: "-0.03em" }}>41</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, color: C.ink, marginTop: 14 }}>voces argentinas</div>
        <Nota style={{ marginTop: 10, fontSize: 21 }}>28 femeninas · 13 masculinas</Nota>
      </div>

      {/* l6: la conversación queda en tu panel */}
      <div style={{
        position: "absolute", left: 1290, top: 300, width: 520, background: "#fff", borderRadius: 26, border: `2px solid ${C.line}`,
        boxShadow: "0 24px 60px rgba(11,18,32,0.14)", padding: "22px 26px", opacity: Math.min(1, pConv * 1.4), transform: `scale(${0.9 + 0.1 * pConv})`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Avatar id="lucia" size={56} />
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink, lineHeight: 1.05 }}>Conversación con Lucía</div>
            <Nota style={{ marginTop: 4 }}>WhatsApp · hoy 10:42</Nota>
          </div>
        </div>
        <div style={{ marginTop: 18, background: C.bg2, borderRadius: 16, padding: "12px 16px", opacity: win(t, t6 + 2.8) }}>
          <div style={{ fontFamily: F.body, fontSize: 21, lineHeight: 1.35, color: C.ink }}><b>Lucía:</b> ¿Tienen turno el jueves?</div>
          <div style={{ fontFamily: F.body, fontSize: 21, lineHeight: 1.35, color: C.ink }}><b style={{ color: C.accent }}>Agente:</b> Sí, a las 10. Te lo reservo.</div>
        </div>
        <div style={{ display: "flex", gap: 14, marginTop: 14, opacity: win(t, t6 + 3.5) }}>
          <div style={{ flex: 1 }}>
            <Nota style={{ fontSize: 15 }}>DATOS</Nota>
            <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, marginTop: 2 }}>Turno: jueves 10 h</div>
          </div>
          <div style={{ flex: 1 }}>
            <Nota style={{ fontSize: 15 }}>RESULTADO</Nota>
            <div style={{ marginTop: 4, opacity: win(t, t6 + 4.2) }}><Estado label="Resuelta" tono="ok" icon={<Icon name="check" size={20} color={C.ok} />} /></div>
          </div>
        </div>
        <Nota style={{ marginTop: 14, fontSize: 15, textAlign: "right" }}>datos ilustrativos</Nota>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 2. todo en uno ----------

const ITEMS_IZQ = ["Número argentino incluido", "WhatsApp", "Voces argentinas"];
const ITEMS_DER = ["Derivación a tu equipo", "Reportes", "Precio en pesos"];
const TC = { x: 960, y: 600 };

export const TodoEnUno: React.FC = () => {
  const t = useT();
  const head = useIn(0.05, 0.6);
  const pAg = usePop(0.1);
  const ticks = [...ITEMS_IZQ, ...ITEMS_DER].map((_, i) => usePop(0.6 + i * 0.6));
  const plan = useIn(4.4, 0.5);
  const fila = (txt: string, i: number, der: boolean) => {
    const p = ticks[i];
    const on = t > 0.6 + i * 0.6 + 0.15 ? 1 : 0;
    return (
      <div key={txt} style={{
        display: "flex", alignItems: "center", gap: 20, flexDirection: der ? "row" : "row-reverse", opacity: Math.min(1, p * 1.5),
        transform: `translateX(${(1 - p) * (der ? 24 : -24)}px)`, height: 120,
      }}>
        <Check on={on} size={58} />
        <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 38, color: C.ink, whiteSpace: "nowrap" }}>{txt}</span>
      </div>
    );
  };
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 120, top: 64, right: 120, opacity: head, transform: `translateY(${(1 - head) * 16}px)` }}>
        <Eyebrow>Todo en uno</Eyebrow>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, lineHeight: 1.08, color: C.ink, marginTop: 12, letterSpacing: "-0.015em" }}>
          Un solo servicio, <span style={{ color: C.accent }}>un precio por mes en pesos.</span>
        </div>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {[0, 1, 2].flatMap((i) => {
          // Del aro del agente al tilde de cada ítem
          const y = 420 + i * 180;
          return [-1, 1].map((lado) => {
            const x = lado < 0 ? 780 : 1140;
            const ang = Math.atan2(y - TC.y, x - TC.x);
            const r = 150;
            return (
              <path key={`${i}${lado}`} d={`M ${TC.x + r * Math.cos(ang)} ${TC.y + r * Math.sin(ang)} L ${x} ${y}`} stroke={C.line2} strokeWidth={4}
                strokeDasharray="3 12" strokeLinecap="round" opacity={ticks[i + (lado < 0 ? 0 : 3)] * 0.9} />
            );
          });
        })}
      </svg>
      <div style={{ position: "absolute", right: 1920 - 770, top: 360, display: "flex", flexDirection: "column", gap: 60 }}>
        {ITEMS_IZQ.map((txt, i) => fila(txt, i, false))}
      </div>
      <div style={{ position: "absolute", left: 1150, top: 360, display: "flex", flexDirection: "column", gap: 60 }}>
        {ITEMS_DER.map((txt, i) => fila(txt, i + 3, true))}
      </div>
      <Agente t={t} cx={TC.x} cy={TC.y} size={190} p={pAg} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 900, display: "flex", justifyContent: "center" }}>
        <PlanBadge p={plan}>Número, llamadas por teléfono y WhatsApp: desde el plan Mostrador</PlanBadge>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 3. para desarrolladores ----------

const DC = { x: 960, y: 610 };
const L_API: Curva = { a: { x: 700, y: DC.y }, c: { x: 760, y: DC.y }, b: { x: DC.x - 135, y: DC.y } };
const L_MCP: Curva = { a: { x: 1220, y: DC.y }, c: { x: 1160, y: DC.y }, b: { x: DC.x + 135, y: DC.y } };

const DevCard: React.FC<{ left: number; p: number; titulo: string; icon: React.ReactNode; children: React.ReactNode }> = ({ left, p, titulo, icon, children }) => (
  <div style={{
    position: "absolute", left, top: 470, width: 540, height: 280, background: "#fff", borderRadius: 28, border: `2px solid ${C.line}`, boxShadow: shadowCard,
    padding: "28px 34px", opacity: Math.min(1, p * 1.4), transform: `translateY(${(1 - p) * 24}px)`,
  }}>
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <div style={{ width: 64, height: 64, borderRadius: 18, background: C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>{icon}</div>
      <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 64, color: C.ink, lineHeight: 1 }}>{titulo}</span>
    </div>
    <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 34, lineHeight: 1.25, color: C.ink2, marginTop: 24 }}>{children}</div>
  </div>
);

export const Desarrolladores: React.FC = () => {
  const t = useT();
  const head = useIn(0.05, 0.6);
  const pAg = usePop(0.1);
  const pApi = usePop(0.9);
  const pMcp = usePop(2.3);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 120, top: 64, right: 120, opacity: head, transform: `translateY(${(1 - head) * 16}px)` }}>
        <Eyebrow>Para desarrolladores</Eyebrow>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 60, lineHeight: 1.08, color: C.ink, marginTop: 12, letterSpacing: "-0.015em" }}>
          Conectalo a tu sistema <span style={{ color: C.accent }}>o manejalo con tu agente.</span>
        </div>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Linea curva={L_API} p={pApi} />
        <Linea curva={L_MCP} p={pMcp} />
      </svg>
      <DevCard left={160} p={pApi} titulo="API" icon={<Glyph name="db" size={36} color={C.accent} />}>
        Agentes, llamadas y voces desde tu sistema
      </DevCard>
      <DevCard left={1220} p={pMcp} titulo="MCP" icon={<Glyph name="chat" size={36} color={C.accent} />}>
        Desde Claude, Cursor o tu agente de programación
      </DevCard>
      <Agente t={t} cx={DC.x} cy={DC.y} size={180} p={pAg} />
      <Paquete t={t} curva={L_API} a={1.5} b={2.1}>{"{ }"}</Paquete>
      <Paquete t={t} curva={L_MCP} a={2.9} b={3.5}>{"{ }"}</Paquete>
      <Paquete t={t} curva={L_API} a={3.6} b={4.2} back color={C.ok}><Icon name="check" size={22} color="#fff" /></Paquete>
    </AbsoluteFill>
  );
};

// ---------- 4. cierre ----------

export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const title = useIn(0.4, 0.7);
  const url = useIn(1.0, 0.6);
  const tel = useIn(1.8, 0.6);
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


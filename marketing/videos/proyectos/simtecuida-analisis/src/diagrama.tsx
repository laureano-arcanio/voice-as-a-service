import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import envs from "../../../public/proyectos/simtecuida-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Wave, useIn, usePop } from "../../../src/comun/ui";
import { Pie, useT } from "./escenas";
import { AT } from "./timeline";

// ---------- piezas del diagrama: el lenguaje de la landing (videos landing-plataforma y atencion-punta-a-punta de la
// home, y los íconos de Channels.astro): logo con aro de puntos, curvas punteadas, paquetes que viajan y tarjetas blancas ----------

type Pt = { x: number; y: number };
type Curva = { a: Pt; c: Pt; b: Pt };
const q = (k: number, { a, c, b }: Curva): Pt => ({
  x: (1 - k) ** 2 * a.x + 2 * (1 - k) * k * c.x + k ** 2 * b.x,
  y: (1 - k) ** 2 * a.y + 2 * (1 - k) * k * c.y + k ** 2 * b.y,
});
const d = ({ a, c, b }: Curva) => `M ${a.x} ${a.y} Q ${c.x} ${c.y} ${b.x} ${b.y}`;

const Paquete: React.FC<{ t: number; curva: Curva; a: number; b: number; color?: string; children: React.ReactNode }> = ({ t, curva, a, b, color = C.accent, children }) => {
  if (t < a - 0.1 || t > b + 0.25) return null;
  const k = interpolate(t, [a, b], [0, 1], { ...CLAMP, easing: EASE });
  const p = q(k, curva);
  const o = Math.min(interpolate(t, [a - 0.1, a + 0.05], [0, 1], CLAMP), interpolate(t, [b, b + 0.25], [1, 0], CLAMP));
  return (
    <div style={{
      position: "absolute", left: p.x, top: p.y, transform: "translate(-50%, -50%)", opacity: o, background: color, color: "#fff", borderRadius: 999,
      padding: "8px 16px", fontFamily: F.mono, fontSize: 22, display: "flex", alignItems: "center", gap: 8, boxShadow: "0 8px 20px rgba(36,86,230,0.35)", whiteSpace: "nowrap",
    }}>
      {children}
    </div>
  );
};

const Aro: React.FC<{ t: number; cx: number; cy: number; r: number; on: number }> = ({ t, cx, cy, r, on }) => {
  const n = 40;
  const head = (t * 9) % n;
  return (
    <svg width={r * 2 + 30} height={r * 2 + 30} style={{ position: "absolute", left: cx - r - 15, top: cy - r - 15, overflow: "visible", opacity: on }}>
      {Array.from({ length: n }).map((_, i) => {
        const ang = (i / n) * Math.PI * 2 - Math.PI / 2;
        const dd = (head - i + n) % n;
        const lit = Math.max(0, 1 - dd / 9);
        return <circle key={i} cx={r + 15 + r * Math.cos(ang)} cy={r + 15 + r * Math.sin(ang)} r={5 + 2 * lit} fill={lit > 0.05 ? C.accent : C.line2} opacity={0.55 + 0.45 * lit} />;
      })}
    </svg>
  );
};

/** Ícono de canal en su baldosa, como en la sección Canales de la home. */
const Baldosa: React.FC<{ canal: "phone" | "wa"; size?: number }> = ({ canal, size = 68 }) => (
  <div style={{
    width: size, height: size, flexShrink: 0, borderRadius: size * 0.28, display: "flex", alignItems: "center", justifyContent: "center",
    background: canal === "wa" ? "linear-gradient(135deg, #3ee58a, #0c9467)" : "linear-gradient(135deg, #5b86ff, #2456e6)", boxShadow: "0 8px 16px rgba(11,18,32,.12)",
  }}>
    <Icon name={canal} size={size * 0.56} color="#fff" />
  </div>
);

export const Avatar: React.FC<{ id: "valentina" | "lucas" | "sofia"; size: number; ring?: string; gray?: number }> = ({ id, size, ring, gray = 0 }) => (
  <div style={{ width: size, height: size, borderRadius: "50%", flexShrink: 0, background: "#fff", boxShadow: ring ? `0 0 0 4px ${ring}` : "0 4px 12px rgba(11,18,32,.14)" }}>
    <Img src={staticFile(`proyectos/simtecuida-analisis/voces/${id}.svg`)} style={{ width: size, height: size, borderRadius: "50%", filter: gray ? `grayscale(${gray})` : undefined }} />
  </div>
);

// ---------- 3. el diagrama ----------

// Momentos de a3 (s desde que arranca la voz; por las pausas de la toma): "Un agente con IA atiende a toda hora" 0,1 ·
// "su línea," 2,3 · "el cero ochocientos" 2,8 · "y el WhatsApp." 3,45 · "Lo que necesita una persona" 4,5 ·
// "pasa a su equipo," 5,85 · "y todo queda en el panel." 6,85–8,05
const M = { agente: 0.1, linea: 2.3, ochocientos: 2.8, whatsapp: 3.45, persona: 4.5, equipo: 5.85, panel: 6.85 };

const CANALES = [
  { canal: "phone" as const, titulo: "Línea telefónica", sub: "un número nuevo", cy: 350, at: M.linea, dash: false },
  { canal: "phone" as const, titulo: "0800", sub: "opcional, si lo quieren", cy: 480, at: M.ochocientos, dash: true },
  { canal: "wa" as const, titulo: "WhatsApp", sub: "llamadas, voz y texto", cy: 610, at: M.whatsapp, dash: false },
];
const AG = { x: 960, y: 480 };
const R = 112;
const ENTRADAS: Curva[] = CANALES.map((c) => ({ a: { x: 520, y: c.cy }, c: { x: 720, y: c.cy }, b: { x: AG.x - R - 8, y: AG.y } }));
const SALIDA: Curva = { a: { x: AG.x + R + 8, y: AG.y }, c: { x: 1260, y: AG.y }, b: { x: 1392, y: 480 } };
const BAJA_AG: Curva = { a: { x: AG.x, y: 668 }, c: { x: AG.x, y: 720 }, b: { x: AG.x, y: 772 } };
const BAJA_EQ: Curva = { a: { x: 1600, y: 668 }, c: { x: 1600, y: 720 }, b: { x: 1600, y: 772 } };
const EQUIPO = [
  { id: "valentina" as const, t: "Persona de turno" },
  { id: "lucas" as const, t: "Si no atiende, la siguiente" },
  { id: "sofia" as const, t: "Y la siguiente" },
];
const CHIPS = ["A quién se pasó", "Cuánto tardó", "Cómo terminó"];

/** 3. La solución: canales → logo de Atentina → su equipo, y todo → panel. */
export const Diagrama: React.FC = () => {
  const t = useT();
  const v = (s: number) => AT.a3 + s;
  const ag = usePop(v(M.agente));
  const rot = useIn(v(M.agente + 0.5), 0.5);
  const canales = CANALES.map((c) => useIn(v(c.at), 0.45));
  const equipo = useIn(v(M.persona), 0.5);
  const salida = interpolate(t, [v(M.persona), v(M.persona + 0.4)], [0, 1], CLAMP);
  const on = interpolate(t, [v(M.equipo), v(M.equipo + 0.25)], [0, 1], CLAMP);
  const panel = useIn(v(M.panel), 0.5);
  const env = envs.a3;
  const i = Math.round((t - v(0)) * 30);
  const talk = i >= 0 && i < env.length ? env[i] * 0.6 : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="La solución" text="Un agente en cada canal," accent="que sabe a quién derivar." size={60} />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRADAS.map((e, n) => <path key={n} d={d(e)} stroke={C.accent} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={canales[n] * 0.75} />)}
        <path d={d(SALIDA)} stroke={C.accent} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={salida * 0.75} />
        <path d={d(BAJA_AG)} stroke={C.accent} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={panel * 0.75} />
        <path d={d(BAJA_EQ)} stroke={C.accent} strokeWidth={5} strokeDasharray="3 13" strokeLinecap="round" fill="none" opacity={panel * 0.75} />
      </svg>

      {CANALES.map((c, n) => (
        <div key={c.titulo} style={{
          position: "absolute", left: 120, top: c.cy - 56, width: 400, height: 112, boxSizing: "border-box", padding: "0 22px", display: "flex", alignItems: "center", gap: 18,
          background: "#fff", border: c.dash ? `3px dashed ${C.line2}` : `2px solid ${C.line}`, borderRadius: 22, boxShadow: shadowCard, opacity: canales[n], transform: `translateX(${(1 - canales[n]) * -30}px)`,
        }}>
          <Baldosa canal={c.canal} />
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, whiteSpace: "nowrap" }}>{c.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 23, color: C.muted, whiteSpace: "nowrap" }}>{c.sub}</div>
          </div>
        </div>
      ))}

      <div style={{ position: "absolute", left: AG.x - 300, width: 600, top: 278, display: "flex", justifyContent: "center", alignItems: "center", gap: 14, opacity: rot }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink }}>Su agente</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 14px", background: C.accentSoft, border: "2px solid #c9d6fb", borderRadius: 999, fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.accent2 }}>
          <Icon name="clock" size={24} color={C.accent} />Las 24 horas
        </div>
      </div>
      <Aro t={t} cx={AG.x} cy={AG.y} r={R} on={rot} />
      <div style={{ position: "absolute", left: AG.x - 85, top: AG.y - 85, transform: `scale(${ag})` }}>
        <AgenteLogo size={170} talk={talk} />
      </div>
      <div style={{ position: "absolute", left: AG.x - 280, width: 560, top: 612, textAlign: "center", fontFamily: F.body, fontSize: 24, lineHeight: 1.1, color: C.ink2, opacity: rot }}>
        Asistente virtual · no da indicaciones médicas
      </div>

      <div style={{ position: "absolute", left: 1140, top: 420, width: 240, textAlign: "center", fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.accent, opacity: salida }}>deriva con minuta</div>

      <div style={{
        position: "absolute", left: 1400, top: 290, width: 400, height: 378, boxSizing: "border-box", padding: "22px 24px", background: "#fff", border: `2px solid ${C.line}`, borderRadius: 24,
        boxShadow: shadowCard, opacity: equipo, transform: `translateX(${(1 - equipo) * 30}px)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Icon name="users" size={32} color={C.accent} />
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Su equipo</div>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 23, color: C.muted, marginTop: 2 }}>La guardia, por rotación</div>
        <div style={{ marginTop: 14, display: "grid", gap: 10 }}>
          {EQUIPO.map((e, n) => {
            const a = n === 0 ? on : 0;
            return (
              <div key={e.t} style={{ display: "flex", alignItems: "center", gap: 12, height: 76, padding: "0 12px", borderRadius: 16, background: a > 0.5 ? C.accentSoft : C.bg2, border: `2px solid ${a > 0.5 ? C.accent : C.line}` }}>
                <Avatar id={e.id} size={54} />
                <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 21, lineHeight: 1.15, color: a > 0.5 ? C.accent2 : C.ink2 }}>{e.t}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{
        position: "absolute", left: 120, top: 776, width: 1680, height: 190, boxSizing: "border-box", padding: "0 38px", display: "flex", alignItems: "center", gap: 26,
        background: C.accentSoft, border: `2px solid ${C.accent}`, borderRadius: 24, opacity: panel, transform: `translateY(${(1 - panel) * 24}px)`,
      }}>
        <div style={{ width: 92, height: 92, flexShrink: 0, borderRadius: 24, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", border: `2px solid ${C.accent}` }}>
          <Icon name="chart" size={56} color={C.accent} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, color: C.ink }}>El panel</div>
          <div style={{ fontFamily: F.body, fontSize: 27, color: C.ink2 }}>Todo, lo del agente y lo de su equipo.</div>
        </div>
        <div style={{ display: "flex", gap: 14 }}>
          {CHIPS.map((x) => <div key={x} style={{ padding: "14px 22px", background: "#fff", border: `2px solid ${C.line2}`, borderRadius: 999, fontFamily: F.body, fontWeight: 700, fontSize: 25, color: C.ink, whiteSpace: "nowrap" }}>{x}</div>)}
        </div>
      </div>

      {ENTRADAS.map((e, n) => (
        <Paquete key={n} t={t} curva={e} a={v(CANALES[n].at + 0.15)} b={v(CANALES[n].at + 0.95)} color={CANALES[n].canal === "wa" ? C.wa : C.accent}>
          {n === 2 ? "Aa" : <Wave n={5} h={22} />}
        </Paquete>
      ))}
      <Paquete t={t} curva={SALIDA} a={v(M.persona + 0.3)} b={v(M.equipo)}>minuta</Paquete>
      <Paquete t={t} curva={BAJA_AG} a={v(M.panel)} b={v(M.panel + 0.7)}>registro</Paquete>
      <Paquete t={t} curva={BAJA_EQ} a={v(M.panel + 0.15)} b={v(M.panel + 0.85)}>registro</Paquete>

      <Pie fuente="Con el nombre que ustedes elijan y voz con acento argentino." />
    </AbsoluteFill>
  );
};

// ---------- 4. el recorrido ----------

// Momentos: a4a "Reconoce..." 0,1 · "Si no aparece..." 2,3; a4b "Si detecta..." 0,1 · "Y deriva..." 3,15 (s desde que arranca cada voz)
const useCard = (t: number, a: number, b: number) => ({
  p: interpolate(t, [a - 0.1, a + 0.35], [0, 1], { ...CLAMP, easing: EASE }),
  on: Math.min(interpolate(t, [a, a + 0.2], [0, 1], CLAMP), interpolate(t, [b, b + 0.3], [1, 0], CLAMP)),
});

const Paso: React.FC<{ n: number; titulo: string; texto: string; p: number; on: number; left: number; children: React.ReactNode }> = ({ n, titulo, texto, p, on, left, children }) => (
  <div style={{
    position: "absolute", left, top: 218, width: 405, height: 510, boxSizing: "border-box", padding: "24px 26px", background: on > 0.5 ? C.accentSoft : "#fff", border: `2px solid ${on > 0.5 ? C.accent : C.line}`,
    borderRadius: 24, boxShadow: shadowCard, opacity: p, transform: `translateY(${(1 - p) * 26}px) scale(${1 + 0.015 * on})`,
  }}>
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <div style={{ width: 46, height: 46, flexShrink: 0, borderRadius: 23, display: "flex", alignItems: "center", justifyContent: "center", background: on > 0.5 ? C.accent : C.accentSoft, color: on > 0.5 ? "#fff" : C.accent, fontFamily: F.display, fontWeight: 800, fontSize: 26 }}>{n}</div>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 31, lineHeight: 1.08, color: C.ink }}>{titulo}</div>
    </div>
    <div style={{ height: 212, marginTop: 14, position: "relative" }}>{children}</div>
    <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.26, color: C.ink2, marginTop: 8 }}>{texto}</div>
  </div>
);

const Chip: React.FC<{ children: React.ReactNode; on?: boolean; style?: React.CSSProperties }> = ({ children, on, style }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 10, padding: "10px 18px", borderRadius: 14, background: on ? C.accentSoft : "#fff", border: `2px solid ${on ? C.accent : C.line2}`,
    fontFamily: F.body, fontWeight: 700, fontSize: 24, color: on ? C.accent2 : C.ink2, whiteSpace: "nowrap", boxSizing: "border-box", ...style,
  }}>{children}</div>
);

const COLA = ["Presupuesto", "Guardia hoy", "Posible emergencia"];

/** 4. El recorrido de cada consulta: los cuatro pasos y la aclaración de emergencias. */
export const Recorrido: React.FC = () => {
  const t = useT();
  const a = (s: number) => AT.a4a + s;
  const b = (s: number) => AT.a4b + s;
  const c1 = useCard(t, a(0.1), a(2.2));
  const c2 = useCard(t, a(2.3), b(0));
  const c3 = useCard(t, b(0.1), b(3.05));
  const c4 = useCard(t, b(3.15), AT.a4c);
  const encontrado = interpolate(t, [a(1.1), a(1.5)], [0, 1], { ...CLAMP, easing: EASE });
  const pide = [0, 1, 2].map((i) => interpolate(t, [a(3.8 + i * 0.5), a(4.1 + i * 0.5)], [0, 1], { ...CLAMP, easing: EASE }));
  const sube = interpolate(t, [b(1.5), b(2.3)], [0, 1], { ...CLAMP, easing: EASE });
  const pasa = interpolate(t, [b(3.8), b(4.2)], [0, 1], { ...CLAMP, easing: EASE });
  const bannerIn = useIn(b(0.1), 0.5);
  const banner = interpolate(t, [AT.a4c - 0.1, AT.a4c + 0.3], [0, 1], { ...CLAMP, easing: EASE });
  // La cola: la posible emergencia pasa de última a primera; las otras bajan un lugar.
  const y = (n: number) => (n === 2 ? 2 - 2 * sube : n + sube) * 70;
  return (
    <AbsoluteFill>
      <Headline eyebrow="El recorrido de cada consulta" text="Saber quién llama," accent="y que lo urgente pase primero." size={60} />

      <Paso n={1} left={120} titulo="Reconoce por el teléfono" texto="Busca el número en la ficha: sabe si ya es cliente sin preguntar." p={c1.p} on={c1.on}>
        <div style={{ display: "grid", gap: 14, justifyItems: "center", paddingTop: 16 }}>
          <Chip style={{ width: "100%", fontFamily: F.mono, fontSize: 26 }}><Icon name="phone" size={28} color={C.accent} />11 5555-0142</Chip>
          <div style={{ opacity: encontrado, transform: `scale(${0.9 + 0.1 * encontrado})` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 22px", borderRadius: 999, background: C.okSoft, border: "2px solid #b6e6cb", fontFamily: F.body, fontWeight: 700, fontSize: 26, color: "#11734a" }}>
              <Icon name="check" size={30} color={C.ok} />Ya es cliente
            </div>
          </div>
        </div>
      </Paso>

      <Paso n={2} left={545} titulo="Si no aparece, pregunta" texto="Si es nuevo, toma los datos que ustedes ya piden." p={c2.p} on={c2.on}>
        <div style={{ display: "grid", gap: 12, paddingTop: 8 }}>
          {["Nombre", "DNI", "Otro dato de contacto"].map((x, i) => (
            <div key={x} style={{ opacity: pide[i], transform: `translateX(${(1 - pide[i]) * 18}px)` }}>
              <Chip style={{ width: "100%" }}>{x}</Chip>
            </div>
          ))}
        </div>
      </Paso>

      <Paso n={3} left={970} titulo="Detecta señales de emergencia" texto="Si puede serlo, le da prioridad y pide solo lo mínimo. Lo demás se ordena por motivo." p={c3.p} on={c3.on}>
        <div style={{ position: "relative", height: 212 }}>
          {COLA.map((x, n) => (
            <div key={x} style={{ position: "absolute", left: 0, right: 0, top: y(n) + 2, zIndex: n === 2 ? 2 : 1 }}>
              <Chip on={n === 2 && sube > 0.3} style={{ width: "100%" }}>{x}{n === 2 && sube > 0.8 ? <span style={{ fontFamily: F.mono, fontSize: 18, color: C.accent }}>PRIMERO</span> : null}</Chip>
            </div>
          ))}
        </div>
      </Paso>

      <Paso n={4} left={1395} titulo="Deriva por rotación" texto="Pasa a la persona de turno; si no atiende, a la siguiente. Antes de atender, oye una minuta breve." p={c4.p} on={c4.on}>
        <div style={{ display: "flex", justifyContent: "center", gap: 18, paddingTop: 26 }}>
          {(["valentina", "lucas", "sofia"] as const).map((id, i) => (
            <div key={id} style={{ display: "grid", justifyItems: "center", gap: 10, opacity: i === 0 ? 1 - 0.55 * pasa : i === 1 ? 0.45 + 0.55 * pasa : 0.45 }}>
              <Avatar id={id} size={92} gray={i === 0 ? pasa : i === 1 ? 1 - pasa : 1} ring={(i === 0 && pasa < 0.5) || (i === 1 && pasa >= 0.5) ? C.accent : undefined} />
            </div>
          ))}
        </div>
        <div style={{ textAlign: "center", fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.accent2, marginTop: 18 }}>{pasa > 0.5 ? "La siguiente" : "Persona de turno"}</div>
      </Paso>

      {/* La aclaración: priorización, no un servicio de emergencias (PDF v2, página 3) */}
      <div style={{
        position: "absolute", left: 120, right: 120, top: 752, height: 222, boxSizing: "border-box", padding: "20px 36px", display: "flex", flexDirection: "column", justifyContent: "center",
        background: banner > 0.5 ? C.accentSoft : "#fff", border: `3px solid ${banner > 0.5 ? C.accent : C.line}`, borderRadius: 24, opacity: bannerIn, transform: `translateY(${(1 - bannerIn) * 20}px) scale(${0.985 + 0.015 * banner})`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 21, letterSpacing: "0.08em", color: C.accent }}>EMERGENCIAS: PRIORIZAR LA ATENCIÓN</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 42, lineHeight: 1.1, color: C.ink, marginTop: 8 }}>
          Es priorización de la atención, <span style={{ color: C.accent }}>no un servicio de emergencias.</span>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.28, color: C.ink2, marginTop: 8 }}>
          No da indicaciones médicas. Puede no reconocer todos los casos: el criterio se prueba con ustedes antes de salir en vivo, y SIM define qué se dice si nadie del equipo atiende.
        </div>
      </div>

      <Pie fuente="Número de ejemplo, inventado." />
    </AbsoluteFill>
  );
};

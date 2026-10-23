import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/cimepa-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { CodeWindow, Ok, Typed } from "../../../src/comun/code";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Link, useIn, usePop, Wave } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// Los tres flujos de la hoja 3 del PDF ("Entra una llamada", "Llama un empleado", "Llama la IA"), uno por escena.

type P = { x: number; y: number };
const bez = (a: P, c: P, b: P, k: number): P => ({
  x: (1 - k) * (1 - k) * a.x + 2 * (1 - k) * k * c.x + k * k * b.x,
  y: (1 - k) * (1 - k) * a.y + 2 * (1 - k) * k * c.y + k * k * b.y,
});
export type Curva = { a: P; b: P; c: P; d: string };
export const curva = (a: P, b: P, c: P = { x: (a.x + b.x) / 2, y: a.y }): Curva => ({ a, b, c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` });

/** Paquete que viaja por una curva entre t0 y t1 (s de la escena). */
export const Paquete: React.FC<{ k: Curva; t0: number; t1: number; children: React.ReactNode; bg?: string; w?: number }> = ({ k, t0, t1, children, bg = C.accent, w = 52 }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const u = interpolate(t, [t0, t1], [0, 1], { ...CLAMP, easing: EASE });
  const o = interpolate(t, [t0 - 0.1, t0, t1, t1 + 0.25], [0, 1, 1, 0], CLAMP);
  const p = bez(k.a, k.c, k.b, u);
  return (
    <div style={{
      position: "absolute", left: p.x - w / 2, top: p.y - 26, width: w, height: 52, borderRadius: 26, opacity: o,
      background: bg, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 22px rgba(36,86,230,.35)",
    }}>
      {children}
    </div>
  );
};

/** Nodo del diagrama: tarjeta con ícono, título y bajada; `on` lo enciende con el acento. */
const Nodo: React.FC<{
  x: number; y: number; w: number; h: number; p: number; on?: number; icon: React.ReactNode; titulo: string; sub?: string;
}> = ({ x, y, w, h, p, on = 0, icon, titulo, sub }) => (
  <div style={{
    position: "absolute", left: x, top: y, width: w, height: h, boxSizing: "border-box", padding: "0 24px", display: "flex", alignItems: "center", gap: 18,
    background: on > 0.5 ? C.accentSoft : "#fff", border: `2px solid ${on > 0.5 ? C.accent : C.line}`, borderRadius: 20,
    boxShadow: on > 0.05 ? `0 0 0 ${8 * on}px rgba(36,86,230,.12), ${shadowCard}` : shadowCard,
    opacity: p, transform: `scale(${(0.92 + 0.08 * p) * (1 + 0.03 * on)})`,
  }}>
    <div style={{ width: 58, height: 58, flex: "none", borderRadius: 29, background: on > 0.5 ? "#fff" : C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>{icon}</div>
    <div>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 29, lineHeight: 1.1, color: on > 0.5 ? C.accent : C.ink, whiteSpace: "nowrap" }}>{titulo}</div>
      {sub ? <div style={{ fontFamily: F.body, fontSize: 20, color: C.muted, marginTop: 4, whiteSpace: "nowrap" }}>{sub}</div> : null}
    </div>
  </div>
);

const useTalk = (id: keyof typeof envs, at: number, k = 0.6) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const env = envs[id];
  const i = frame - Math.round(at * fps);
  return i >= 0 && i < env.length ? env[i] * k : 0;
};

// c3: "Entra una llamada," 0,1 · "y la atiende la IA." 1,37 · "Resuelve," 2,83 · "o la deriva al celular del empleado," 3,6 ·
// "con un resumen." 5,63–6,57
const E = { atiende: 1.37, resuelve: 2.83, deriva: 3.6, resumen: 5.63 };
const AG_E = { x: 960, y: 500 };
const CLI_NUM = curva({ x: 350, y: 525 }, { x: 392, y: 525 });
const NUM_AG = curva({ x: 802, y: 525 }, { x: AG_E.x - 92, y: AG_E.y });
const AG_RES = curva({ x: AG_E.x + 92, y: AG_E.y - 20 }, { x: 1300, y: 355 });
const AG_EMP = curva({ x: AG_E.x + 92, y: AG_E.y + 20 }, { x: 1300, y: 620 });

/** 2. Entra una llamada: cliente → número de la empresa → la IA, que resuelve o deriva al celular con un resumen. */
export const Entra: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.c3 + s;
  const cliente = useIn(v(0), 0.5);
  const numero = useIn(v(0.3), 0.5);
  const agente = usePop(v(0.5));
  const atiende = interpolate(t, [v(E.atiende), v(E.atiende + 0.3)], [0, 1], CLAMP);
  const resuelve = useIn(v(E.resuelve - 0.1), 0.5);
  const resOn = interpolate(t, [v(E.resuelve), v(E.resuelve + 0.3), v(E.deriva), v(E.deriva + 0.3)], [0, 1, 1, 0], CLAMP);
  const empleado = useIn(v(E.deriva), 0.5);
  const empOn = interpolate(t, [v(E.deriva + 1.3), v(E.deriva + 1.6)], [0, 1], CLAMP);
  const resumen = useIn(v(E.resumen - 0.1), 0.6);
  const nota = useIn(v(4.6), 0.6);
  const talk = useTalk("c3", v(0));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Entra una llamada" text="La atiende la IA:" accent="resuelve, o deriva con un resumen." />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Link d={CLI_NUM.d} color={C.line2} opacity={numero} />
        <Link d={NUM_AG.d} color={C.accent} opacity={agente * 0.5} />
        <Link d={AG_RES.d} color={C.accent} opacity={resuelve * (0.35 + 0.5 * resOn)} />
        <Link d={AG_EMP.d} color={C.accent} opacity={empleado * (0.45 + 0.45 * empOn)} width={5 + 3 * empOn} />
      </svg>

      <Nodo x={120} y={465} w={230} h={120} p={cliente} icon={<Icon name="users" size={32} color={C.ink2} />} titulo="Su cliente" />
      <Nodo x={392} y={465} w={410} h={120} p={numero} icon={<Icon name="phone" size={30} color={C.accent} />} titulo="Número de la empresa" sub="3 o más, argentinos" />

      <div style={{ position: "absolute", left: AG_E.x - 95, top: AG_E.y - 95, width: 190, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente * (1 + 0.04 * atiende)})` }}>
        <AgenteLogo size={190} talk={talk} style={{ filter: `drop-shadow(0 16px 30px rgba(36,86,230,${0.12 + 0.18 * atiende}))` }} />
        <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 20, whiteSpace: "nowrap" }}>
          Asistente de IA · el suyo o el nuestro
        </div>
      </div>

      <Nodo x={1300} y={300} w={440} h={110} p={resuelve} on={resOn} icon={<Icon name="check" size={32} color={C.ok} />} titulo="Resuelve" sub="responde y cierra la llamada" />
      <Nodo x={1300} y={560} w={500} h={120} p={empleado} on={empOn} icon={<Icon name="phone" size={30} color={C.accent} />} titulo="Celular del empleado" sub="su equipo remoto, sin instalar nada" />

      <div style={{
        position: "absolute", left: 1300, top: 712, width: 500, boxSizing: "border-box", padding: "18px 24px", borderRadius: 18,
        background: "#fff", border: `2px solid ${C.accent}`, boxShadow: shadowCard, opacity: resumen, transform: `translateY(${(1 - resumen) * 20}px)`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.06em", color: C.accent }}>RESUMEN PARA EL EMPLEADO</div>
        <div style={{ fontFamily: F.body, fontSize: 23, lineHeight: 1.35, color: C.ink, marginTop: 8 }}>
          Consulta por el estado de su pedido; pide hablar con una persona.
        </div>
      </div>

      <div style={{
        position: "absolute", left: 120, top: 770, width: 1100, display: "flex", alignItems: "center", gap: 14, opacity: nota,
        fontFamily: F.body, fontSize: 25, color: C.ink2,
      }}>
        <Icon name="missed" size={30} color={C.muted} />
        Si no atiende nadie, la IA vuelve a la llamada y toma el mensaje.
      </div>

      <Paquete k={CLI_NUM} t0={v(0.2)} t1={v(0.7)}><Icon name="phone" size={26} color="#fff" /></Paquete>
      <Paquete k={NUM_AG} t0={v(0.75)} t1={v(1.35)}><Icon name="phone" size={26} color="#fff" /></Paquete>
      <Paquete k={AG_EMP} t0={v(E.deriva + 0.1)} t1={v(E.deriva + 1.5)} bg={C.ink} w={124}>
        <span style={{ fontFamily: F.mono, fontSize: 18, color: "#fff" }}>resumen</span>
      </Paquete>

      <Pie hoja="3 / 5" fuente="El resumen es un ejemplo." />
    </AbsoluteFill>
  );
};

// c4: "Un empleado llama desde la app web," 0,27 · "en la compu o el celular:" 2,6 · "elige el contacto," 4,5 · "un clic," 5,7 ·
// "y sale con el número de la empresa." 6,47–8,13
const M4 = { celular: 3.3, elige: 4.5, clic: 5.7, sale: 6.47 };
// Agenda de ejemplo (nombres inventados)
const AGENDA = [
  { n: "Laura Gómez", d: "Consulta del martes", tel: "+54 11 •••• 2481" },
  { n: "Diego Ferrari", d: "Pidió presupuesto", tel: "+54 11 •••• 7730" },
  { n: "Marina Sosa", d: "Seguimiento de la visita", tel: "+54 351 ••• 0194" },
  { n: "Pablo Ruiz", d: "Volver a llamar", tel: "+54 11 •••• 5512" },
  { n: "Ana Torres", d: "Nuevo contacto", tel: "+54 221 ••• 8807" },
];
const ELEGIDO = 2;
const WX = 120, WY = 250, WW = 900, WH = 700;
const ROW0 = WY + 54 + 108;
const ROWH = 82;
const BTN = { x: WX + WW - 40 - 150, w: 150 };
const SALE = curva({ x: WX + WW - 10, y: WY + WH - 50 }, { x: 1610, y: 662 }, { x: 1290, y: 1010 });

/** 3. Llama un empleado: la app web en la compu o el celular, la agenda, un clic, y sale con el número de la empresa. */
export const Empleado: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.c4 + s;
  const win = useIn(v(0.1), 0.6);
  const filas = AGENDA.map((_, i) => useIn(v(0.6 + i * 0.12), 0.4));
  const cel = usePop(v(M4.celular));
  const elige = interpolate(t, [v(M4.elige), v(M4.elige + 0.3)], [0, 1], CLAMP);
  // El cursor va de abajo al botón "Llamar" de la fila elegida y hace clic
  const ir = interpolate(t, [v(M4.elige - 0.2), v(M4.clic - 0.1)], [0, 1], { ...CLAMP, easing: EASE });
  const btnY = ROW0 + ELEGIDO * ROWH + ROWH / 2;
  const cx = interpolate(ir, [0, 1], [640, BTN.x + 100]);
  const cy = interpolate(ir, [0, 1], [880, btnY + 6]);
  const press = interpolate(t, [v(M4.clic), v(M4.clic + 0.1), v(M4.clic + 0.25)], [0, 1, 0], CLAMP);
  const clic = interpolate(t, [v(M4.clic), v(M4.clic + 0.15)], [0, 1], CLAMP);
  const barra = useIn(v(M4.clic + 0.2), 0.4);
  const cliente = useIn(v(M4.sale), 0.5);
  const llega = useIn(v(M4.sale + 0.9), 0.4);
  const seg = Math.max(0, Math.floor(t - v(M4.clic + 0.2)));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Llama un empleado" text="Desde la app web," accent="con el número de la empresa." />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Link d={SALE.d} color={C.accent} opacity={cliente * 0.55} />
      </svg>

      {/* La app web en la compu (pantalla de ejemplo) */}
      <div style={{
        position: "absolute", left: WX, top: WY, width: WW, height: WH, borderRadius: 22, overflow: "hidden", border: `2px solid ${C.line2}`,
        background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.14)", opacity: win, transform: `translateY(${(1 - win) * 40}px)`,
      }}>
        <div style={{ height: 54, background: C.surface2, display: "flex", alignItems: "center", gap: 10, padding: "0 20px", borderBottom: `2px solid ${C.line}` }}>
          {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
          <div style={{ marginLeft: 14, fontFamily: F.mono, fontSize: 17, color: C.muted }}>Atentina · Llamadas del equipo</div>
          <div style={{ flex: 1 }} />
          <div style={{ fontFamily: F.mono, fontSize: 15, color: C.muted, letterSpacing: "0.06em" }}>PANTALLA DE EJEMPLO</div>
        </div>
        <div style={{ padding: "22px 32px 0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Agenda</div>
          <div style={{ width: 360, height: 48, borderRadius: 12, border: `2px solid ${C.line}`, display: "flex", alignItems: "center", padding: "0 16px", fontFamily: F.body, fontSize: 20, color: C.muted }}>
            Buscar contacto
          </div>
        </div>
        {AGENDA.map((c, i) => {
          const on = i === ELEGIDO ? elige : 0;
          return (
            <div key={c.n} style={{
              position: "absolute", left: 20, right: 20, top: ROW0 - WY + i * ROWH, height: ROWH - 8, borderRadius: 14, display: "flex", alignItems: "center",
              padding: "0 20px", gap: 18, background: on > 0.5 ? C.accentSoft : "transparent", border: `2px solid ${on > 0.5 ? C.accent : "transparent"}`,
              opacity: filas[i],
            }}>
              <div style={{ width: 44, height: 44, borderRadius: 22, background: C.surface2, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.body, fontWeight: 700, fontSize: 18, color: C.ink2 }}>
                {c.n.split(" ").map((w) => w[0]).join("")}
              </div>
              <div style={{ width: 300 }}>
                <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 23, color: C.ink }}>{c.n}</div>
                <div style={{ fontFamily: F.body, fontSize: 18, color: C.muted }}>{c.d}</div>
              </div>
              <div style={{ fontFamily: F.mono, fontSize: 18, color: C.ink2 }}>{c.tel}</div>
            </div>
          );
        })}
        {AGENDA.map((c, i) => {
          const sel = i === ELEGIDO;
          return (
            <div key={c.n + "b"} style={{
              position: "absolute", left: BTN.x - WX, top: ROW0 - WY + i * ROWH + 14, width: BTN.w, height: 46, borderRadius: 12, display: "flex",
              alignItems: "center", justifyContent: "center", gap: 8, opacity: filas[i],
              background: sel && clic > 0.5 ? C.ok : sel && elige > 0.5 ? C.accent : "#fff", border: `2px solid ${sel && elige > 0.5 ? "transparent" : C.line}`,
              transform: `scale(${1 - 0.06 * (sel ? press : 0)})`,
            }}>
              <Icon name="phone" size={20} color={sel && elige > 0.5 ? "#fff" : C.accent} />
              <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 19, color: sel && elige > 0.5 ? "#fff" : C.accent }}>Llamar</span>
            </div>
          );
        })}
        <div style={{
          position: "absolute", left: 0, right: 0, bottom: 0, height: 96, background: C.ink, display: "flex", alignItems: "center", gap: 18, padding: "0 30px",
          opacity: barra, transform: `translateY(${(1 - barra) * 96}px)`,
        }}>
          <div style={{ width: 52, height: 52, borderRadius: 26, background: C.ok, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="phone" size={26} color="#fff" />
          </div>
          <div>
            <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 23, color: C.ctaInk }}>Llamando a Marina Sosa</div>
            <div style={{ fontFamily: F.mono, fontSize: 17, color: C.accentOnDark }}>sale con el número de la empresa</div>
          </div>
          <div style={{ flex: 1 }} />
          <Wave n={6} h={30} color={C.accentOnDark} live={barra} />
          <div style={{ fontFamily: F.mono, fontSize: 22, color: C.ctaInk, marginLeft: 12 }}>00:0{Math.min(9, seg)}</div>
        </div>
      </div>

      {/* La misma app en el celular */}
      <div style={{
        position: "absolute", left: 1075, top: 300, width: 270, height: 540, borderRadius: 40, background: C.ink, padding: 12, boxSizing: "border-box",
        boxShadow: "0 24px 60px rgba(11,18,32,.2)", transform: `scale(${cel})`, opacity: Math.min(1, cel * 1.5),
      }}>
        <div style={{ width: "100%", height: "100%", borderRadius: 30, background: "#fff", overflow: "hidden", position: "relative" }}>
          <div style={{ margin: "14px auto 0", width: 70, height: 8, borderRadius: 4, background: C.line }} />
          <div style={{ padding: "18px 18px 8px", fontFamily: F.display, fontWeight: 800, fontSize: 24, color: C.ink }}>Agenda</div>
          {AGENDA.slice(0, 4).map((c, i) => {
            const on = i === ELEGIDO ? elige : 0;
            return (
              <div key={c.n} style={{
                margin: "6px 12px", padding: "10px 12px", borderRadius: 12, background: on > 0.5 ? C.accentSoft : C.surface2,
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 16, color: C.ink, whiteSpace: "nowrap" }}>{c.n}</span>
                <Icon name="phone" size={18} color={on > 0.5 ? C.accent : C.muted} />
              </div>
            );
          })}
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 26, display: "flex", justifyContent: "center" }}>
            <div style={{ width: 64, height: 64, borderRadius: 32, background: clic > 0.5 ? C.ok : C.accent, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon name="phone" size={30} color="#fff" />
            </div>
          </div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 1075, width: 270, top: 856, textAlign: "center", fontFamily: F.mono, fontSize: 18, color: C.muted, opacity: Math.min(1, cel) }}>
        en la compu o el celular
      </div>

      {/* Su cliente recibe la llamada con el número de la empresa */}
      <div style={{
        position: "absolute", left: 1420, top: 420, width: 380, height: 240, boxSizing: "border-box", padding: "26px 28px", borderRadius: 22,
        background: "#fff", border: `2px solid ${llega > 0.5 ? C.accent : C.line}`, boxShadow: shadowCard, opacity: cliente, transform: `translateX(${(1 - cliente) * 30}px)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Icon name="users" size={34} color={C.ink2} />
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Su cliente</div>
        </div>
        <div style={{ marginTop: 20, padding: "14px 18px", borderRadius: 14, background: C.accentSoft, opacity: llega, display: "flex", alignItems: "center", gap: 12 }}>
          <Icon name="phone" size={26} color={C.accent} />
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted }}>TE LLAMA</div>
            <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, whiteSpace: "nowrap" }}>Número de la empresa</div>
          </div>
        </div>
      </div>

      {/* Cursor */}
      <svg width={40} height={48} viewBox="0 0 20 24" style={{ position: "absolute", left: cx, top: cy, opacity: interpolate(t, [v(M4.elige - 0.3), v(M4.elige - 0.1), v(M4.sale), v(M4.sale + 0.3)], [0, 1, 1, 0], CLAMP) }}>
        <path d="M2 2 L2 19 L6.5 15 L9.5 22 L12.5 20.7 L9.6 14 L16 14 Z" fill={C.ink} stroke="#fff" strokeWidth={1.4} strokeLinejoin="round" />
      </svg>

      <Paquete k={SALE} t0={v(M4.sale)} t1={v(M4.sale + 0.9)}><Icon name="phone" size={26} color="#fff" /></Paquete>

      <Pie hoja="3 / 5" fuente="Pantalla y contactos de ejemplo." />
    </AbsoluteFill>
  );
};

// c5: "Llama la IA:" 0,1 · "seguimientos programados por API," 1,6 · "con su contexto" 3,97 · "y sus instrucciones." ~5,0–6,13
const M5 = { programados: 1.6, contexto: 3.97, instrucciones: 5.0 };
const CODE = `{ "agent_id": "seguimiento",
  "contact_id": "…",
  "from_number_id": "…",
  "context": "Seguimiento de la consulta del martes" }`;
// Seguimientos programados de ejemplo
const AGENDADOS = [
  { h: "10:00", n: "Laura Gómez", m: "Seguimiento de la consulta del martes" },
  { h: "10:15", n: "Diego Ferrari", m: "Respuesta al presupuesto" },
  { h: "10:30", n: "Pablo Ruiz", m: "Volver a llamar, pidió a esta hora" },
];
const AG_I = { x: 1240, y: 450 };
const COD_AG = curva({ x: 940, y: 420 }, { x: AG_I.x - 90, y: AG_I.y });
const AG_CLI = curva({ x: AG_I.x + 90, y: AG_I.y }, { x: 1560, y: 450 });

/** 4. Llama la IA: su sistema programa los seguimientos por API, con su contexto y sus instrucciones. */
export const LlamaIA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const v = (s: number) => AT.c5 + s;
  const code = useIn(v(0.2), 0.5);
  const lista = useIn(v(M5.programados + 0.6), 0.5);
  const filas = AGENDADOS.map((_, i) => useIn(v(M5.programados + 0.8 + i * 0.2), 0.4));
  const agente = usePop(v(0.3));
  const ctx = useIn(v(M5.contexto), 0.5);
  const ins = useIn(v(M5.instrucciones), 0.5);
  const cliente = useIn(v(M5.contexto + 0.4), 0.5);
  const ctxOn = interpolate(t, [v(M5.contexto), v(M5.contexto + 0.3)], [0, 1], CLAMP);
  const enCurso = interpolate(t, [v(M5.contexto + 0.6), v(M5.contexto + 0.9)], [0, 1], CLAMP);
  const talk = useTalk("c5", v(0));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Llama la IA: seguimientos programados" text="Por API," accent="con su contexto y sus instrucciones." />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Link d={COD_AG.d} color={C.accent} opacity={code * 0.5} />
        <Link d={AG_CLI.d} color={C.accent} opacity={cliente * 0.5} />
      </svg>

      <div style={{ position: "absolute", left: 120, top: 262, width: 820, opacity: code, transform: `translateY(${(1 - code) * 30}px)` }}>
        <CodeWindow tab="su sistema" method="POST" path="/api/v1/calls" status={t > v(M5.programados + 1.9) ? <Ok>201</Ok> : null} fontSize={21} minHeight={150}>
          <div style={{ position: "relative" }}>
            <div style={{
              position: "absolute", left: -10, right: -10, top: 3 * 31.5, height: 31.5, borderRadius: 6, background: "rgba(157,182,255,.16)", opacity: ctxOn,
            }} />
            <Typed text={CODE} a={v(M5.programados - 0.4)} b={v(M5.programados + 1.6)} t={t} />
          </div>
        </CodeWindow>
      </div>

      <div style={{
        position: "absolute", left: 120, top: 600, width: 820, boxSizing: "border-box", padding: "20px 26px", borderRadius: 20, background: "#fff",
        border: `2px solid ${C.line}`, boxShadow: shadowCard, opacity: lista, transform: `translateY(${(1 - lista) * 20}px)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>
          <Icon name="calendar" size={22} color={C.muted} />PROGRAMADOS · HOY
        </div>
        {AGENDADOS.map((a, i) => (
          <div key={a.h} style={{ display: "flex", alignItems: "center", gap: 18, height: 62, borderTop: i ? `2px solid ${C.line}` : "none", marginTop: i ? 0 : 8, opacity: filas[i] }}>
            <span style={{ fontFamily: F.mono, fontSize: 21, color: C.accent, width: 70 }}>{a.h}</span>
            <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink, width: 180, whiteSpace: "nowrap" }}>{a.n}</span>
            <span style={{ fontFamily: F.body, fontSize: 20, color: C.ink2, whiteSpace: "nowrap" }}>{a.m}</span>
            <div style={{ flex: 1 }} />
            {i === 0 ? (
              <span style={{ borderRadius: 999, padding: "4px 12px", background: C.okSoft, color: C.ok, fontFamily: F.body, fontWeight: 700, fontSize: 16, opacity: enCurso, whiteSpace: "nowrap" }}>en curso</span>
            ) : null}
          </div>
        ))}
        <div style={{ fontFamily: F.body, fontSize: 19, color: C.muted, marginTop: 8 }}>Una a una o en campañas: horario, reintentos y llamadas en paralelo.</div>
      </div>

      <div style={{ position: "absolute", left: AG_I.x - 90, top: AG_I.y - 90, width: 180, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${agente})` }}>
        <AgenteLogo size={180} talk={talk} style={{ filter: "drop-shadow(0 16px 30px rgba(36,86,230,.22))" }} />
        <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 20px", fontFamily: F.mono, fontSize: 20, whiteSpace: "nowrap" }}>
          Asistente de IA
        </div>
      </div>

      <div style={{
        position: "absolute", left: 1560, top: 370, width: 240, height: 160, boxSizing: "border-box", borderRadius: 20, background: "#fff",
        border: `2px solid ${C.line}`, boxShadow: shadowCard, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6,
        opacity: cliente,
      }}>
        <Icon name="users" size={36} color={C.ink2} />
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 26, color: C.ink }}>Laura Gómez</div>
        <div style={{ fontFamily: F.body, fontSize: 17, color: C.muted, textAlign: "center", lineHeight: 1.2 }}>la llama el número<br />de la empresa</div>
      </div>

      {[
        { p: ctx, k: "CONTEXTO", x: "Seguimiento de la consulta del martes", top: 650 },
        { p: ins, k: "INSTRUCCIONES", x: "Las que define su sistema para cada llamada", top: 760 },
      ].map((c) => (
        <div key={c.k} style={{
          position: "absolute", left: 1040, top: c.top, width: 760, height: 88, boxSizing: "border-box", padding: "0 24px", borderRadius: 16,
          display: "flex", alignItems: "center", gap: 20, background: C.accentSoft, border: `2px solid ${C.accent}`,
          opacity: c.p, transform: `translateX(${(1 - c.p) * 24}px)`,
        }}>
          <span style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.06em", color: C.accent, width: 170, flex: "none" }}>{c.k}</span>
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 23, color: C.ink, whiteSpace: "nowrap" }}>{c.x}</span>
        </div>
      ))}

      <Paquete k={COD_AG} t0={v(M5.programados + 1.9)} t1={v(M5.programados + 2.5)} bg={C.ink} w={64}>
        <span style={{ fontFamily: F.mono, fontSize: 20, color: "#fff" }}>{"{ }"}</span>
      </Paquete>
      <Paquete k={AG_CLI} t0={v(M5.contexto + 0.5)} t1={v(M5.contexto + 1.3)}><Icon name="phone" size={26} color="#fff" /></Paquete>

      <Pie hoja="3 / 5" fuente="Contactos y horarios de ejemplo." />
    </AbsoluteFill>
  );
};

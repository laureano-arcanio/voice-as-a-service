import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, Link, useIn, usePop, Wave } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT, DUR, en } from "./timeline";

const useT = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps;
};

type P = { x: number; y: number };
const bez = (a: P, c: P, b: P, k: number): P => ({
  x: (1 - k) ** 2 * a.x + 2 * (1 - k) * k * c.x + k ** 2 * b.x,
  y: (1 - k) ** 2 * a.y + 2 * (1 - k) * k * c.y + k ** 2 * b.y,
});
type Curva = { a: P; b: P; c: P; d: string };
const curva = (a: P, b: P, c: P = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }): Curva => ({ a, b, c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` });

/** Paquete que viaja por una curva entre t0 y t1 (s de la escena) y desaparece al llegar. */
const Paquete: React.FC<{ k: Curva; t0: number; t1: number; children: React.ReactNode; bg?: string; w?: number }> = ({
  k, t0, t1, children, bg = C.accent, w = 60,
}) => {
  const t = useT();
  if (t < t0 || t > t1 + 0.15) return null;
  const s = interpolate(t, [t0, t1], [0, 1], { ...CLAMP, easing: EASE });
  const p = bez(k.a, k.c, k.b, s);
  const o = interpolate(t, [t0, t0 + 0.12, t1, t1 + 0.15], [0, 1, 1, 0], CLAMP);
  return (
    <div style={{
      position: "absolute", left: p.x - w / 2, top: p.y - 24, width: w, height: 48, borderRadius: 24, background: bg, opacity: o,
      display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 20px rgba(36,86,230,.3)",
      fontFamily: F.mono, fontSize: 21, color: "#fff",
    }}>{children}</div>
  );
};

/** Número del recorrido, como en el diagrama del PDF (1 a 4). */
const Paso: React.FC<{ n: number; x: number; y: number; o: number }> = ({ n, x, y, o }) => (
  <div style={{
    position: "absolute", left: x - 19, top: y - 19, width: 38, height: 38, borderRadius: 19, background: C.ink, color: "#fff", opacity: o,
    display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.mono, fontSize: 20,
  }}>{n}</div>
);

// ---------- 3. La integración por dentro (PDF, hoja 3) ----------

const COL = {
  dyn: { x: 120, w: 320, y: 250, h: 500 },
  pa: { x: 530, w: 280, y: 330, h: 270 },
  api: { x: 900, w: 420, y: 250, h: 120 },
  ag: { x: 900, w: 420, y: 400, h: 350 },
  can: { x: 1410, w: 390 },
};
const MODULOS = [
  ["Sales", "leads y oportunidades"],
  ["Customer Service", "casos y contactos"],
  ["Field Service", "órdenes y visitas"],
] as const;
const CANALES = [
  { icon: "phone" as const, b: "Línea argentina", s: "regional, 0800, 0810", y: 250 },
  { icon: "wa" as const, b: "WhatsApp", s: "mensajes y llamadas", y: 366 },
  { icon: "web" as const, b: "Link en el navegador", s: "desde Power Pages", y: 482 },
];
const CLI = { y: 620, h: 130 };
const DYN_PA = curva({ x: 440, y: 465 }, { x: 530, y: 465 });
const PA_API = curva({ x: 810, y: 400 }, { x: 900, y: 310 }, { x: 870, y: 320 });
const AG_LINEA = curva({ x: 1320, y: 470 }, { x: 1410, y: 300 }, { x: 1380, y: 320 });
const CLI_AG = curva({ x: 1410, y: 685 }, { x: 1320, y: 640 }, { x: 1360, y: 680 });
const VUELTA = curva({ x: 1000, y: 750 }, { x: 330, y: 750 }, { x: 665, y: 850 });

export const Integracion: React.FC = () => {
  const t = useT();
  const dyn = useIn(0.3, 0.6);
  const paAt = en("a4", "Power Automate");
  const apiAt = en("a4", "por ápi");
  const hablaAt = en("a4", "el agente habla");
  const vuelveAt = en("a4", "y el resultado");
  const entraAt = en("a5", "Si el cliente");
  const atiendeAt = en("a5", "atiende");
  const casoAt = en("a5", "deja el caso");
  const biAt = en("a5", "Power BI");
  const pa = usePop(paAt - 0.2);
  const api = usePop(apiAt - 0.2);
  const ag = useIn(apiAt + 0.2, 0.5);
  const canales = CANALES.map((_, i) => usePop(hablaAt - 0.2 + i * 0.12));
  const cli = usePop(hablaAt + 0.3);
  const vuelta = useIn(vuelveAt - 0.1, 0.5);
  const bi = useIn(biAt - 0.2, 0.6);
  const hablando = (t > hablaAt && t < vuelveAt) || (t > atiendeAt && t < casoAt) ? 1 : 0;
  const dataverseOn = interpolate(t, [vuelveAt + 1.0, vuelveAt + 1.3, vuelveAt + 2.2, vuelveAt + 2.6, casoAt + 1.0, casoAt + 1.3, casoAt + 2.3, casoAt + 2.7],
    [0, 1, 1, 0, 0, 1, 1, 0], CLAMP);
  const pasos = [useIn(paAt, 0.4), useIn(apiAt, 0.4), useIn(hablaAt + 0.1, 0.4), useIn(vuelveAt, 0.4)];
  const entrante = useIn(entraAt - 0.1, 0.4);
  return (
    <AbsoluteFill>
      <Headline eyebrow="La integración por dentro" text="Dynamics decide, Atentina habla" accent="y el resultado vuelve a Dataverse." size={50} />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Link d={DYN_PA.d} color={C.muted} opacity={pa} />
        <Link d={PA_API.d} color={C.accent} opacity={api} />
        <Link d={`M1110 ${COL.api.y + COL.api.h} L1110 ${COL.ag.y}`} color={C.accent} opacity={ag} />
        <Link d={AG_LINEA.d} color={C.accent} opacity={canales[0]} />
        <Link d={CLI_AG.d} color={C.accent} opacity={entrante} />
        <path d={VUELTA.d} fill="none" stroke={C.accent} strokeWidth={4} strokeDasharray="12 10" opacity={vuelta} strokeDashoffset={-t * 40} />
        <Link d={`M280 ${COL.dyn.y + COL.dyn.h} L280 862`} color={C.muted} opacity={bi} />
        <Link d={`M1250 ${COL.ag.y + COL.ag.h} L1250 862`} color={C.accent} opacity={bi} />
      </svg>

      {/* Dynamics 365 y Dataverse: lo del cliente de Zennon (gris) */}
      <div style={{
        position: "absolute", left: COL.dyn.x, top: COL.dyn.y, width: COL.dyn.w, height: COL.dyn.h, boxSizing: "border-box", padding: "20px 22px",
        borderRadius: 24, background: C.surface2, border: `2px solid ${C.line2}`, opacity: dyn,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.08em", color: C.muted }}>EL CLIENTE DE ZENNON</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink, marginTop: 4 }}>Dynamics 365</div>
        {MODULOS.map(([b, s]) => (
          <div key={b} style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 14, padding: "8px 16px", marginTop: 10 }}>
            <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 23, color: C.ink }}>{b}</div>
            <div style={{ fontFamily: F.body, fontSize: 19, color: C.muted }}>{s}</div>
          </div>
        ))}
        <div style={{
          position: "absolute", left: 22, right: 22, bottom: 20, borderRadius: 14, padding: "10px 16px",
          background: dataverseOn > 0.5 ? C.accent : C.ink, transform: `scale(${1 + 0.04 * dataverseOn})`,
        }}>
          <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 25, color: "#fff" }}>Dataverse</div>
          <div style={{ fontFamily: F.body, fontSize: 19, color: C.ctaMuted }}>registro y actividades</div>
        </div>
      </div>

      {/* Power Automate: lo arma Zennon (gris) */}
      <div style={{
        position: "absolute", left: COL.pa.x, top: COL.pa.y, width: COL.pa.w, height: COL.pa.h, boxSizing: "border-box", padding: "20px 22px",
        borderRadius: 24, background: "#fff", border: `2px solid ${C.line2}`, boxShadow: shadowCard, transform: `scale(${pa})`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.08em", color: C.muted }}>LO ARMA ZENNON</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, lineHeight: 1.05, color: C.ink, marginTop: 6 }}>Power Automate</div>
        <div style={{ background: C.surface2, borderRadius: 14, padding: "10px 14px", marginTop: 14 }}>
          <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 22, color: C.ink }}>Conector Atentina</div>
          <div style={{ fontFamily: F.body, fontSize: 19, lineHeight: 1.3, color: C.ink2 }}>dispara y recibe; escribe en el registro</div>
        </div>
      </div>

      {/* Atentina (azul) */}
      <div style={{
        position: "absolute", left: COL.api.x, top: COL.api.y, width: COL.api.w, height: COL.api.h, boxSizing: "border-box", padding: "16px 24px",
        borderRadius: 22, background: C.accentSoft, border: `3px solid ${C.accent}`, transform: `scale(${api})`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.06em", color: C.accent }}>API /api/v1</div>
        <div style={{ fontFamily: F.body, fontSize: 22, lineHeight: 1.3, color: C.accent2, marginTop: 6 }}>llamadas, campañas, contactos y resultados</div>
      </div>
      <div style={{
        position: "absolute", left: COL.ag.x, top: COL.ag.y, width: COL.ag.w, height: COL.ag.h, boxSizing: "border-box", padding: "20px 24px",
        borderRadius: 26, background: "#fff", border: `3px solid ${C.accent}`, boxShadow: shadowCard, opacity: ag, transform: `translateY(${(1 - ag) * 20}px)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <AgenteLogo size={76} talk={hablando * 0.5} />
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.08em", color: C.accent }}>ATENTINA · EN ARGENTINA</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink }}>El agente</div>
          </div>
        </div>
        {[["Escucha", "lo que dicen"], ["Decide", "con sus reglas"], ["Habla", "con voz argentina y captura los datos"]].map(([b, s]) => (
          <div key={b} style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 12, borderTop: `2px solid ${C.line}`, paddingTop: 10 }}>
            <span style={{ fontFamily: F.body, fontWeight: 800, fontSize: 24, color: C.accent2 }}>{b}</span>
            <span style={{ fontFamily: F.body, fontSize: 21, color: C.ink2 }}>{s}</span>
          </div>
        ))}
        <div style={{ position: "absolute", left: 24, right: 24, bottom: 18, fontFamily: F.mono, fontSize: 16, color: C.muted, letterSpacing: "0.04em" }}>
          + PANEL: TRANSCRIPCIÓN Y RESULTADO
        </div>
      </div>

      {/* Canales y los clientes de sus clientes */}
      {CANALES.map((c, i) => (
        <div key={c.b} style={{
          position: "absolute", left: COL.can.x, top: c.y, width: COL.can.w, height: 100, boxSizing: "border-box", padding: "0 20px",
          display: "flex", alignItems: "center", gap: 16, borderRadius: 20, background: C.accentSoft, border: `2px solid ${C.accent}`,
          transform: `scale(${canales[i]})`,
        }}>
          <div style={{ width: 56, height: 56, borderRadius: 28, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Icon name={c.icon} size={32} color={C.accent} />
          </div>
          <div>
            <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 25, color: C.accent2, whiteSpace: "nowrap" }}>{c.b}</div>
            <div style={{ fontFamily: F.body, fontSize: 19, color: C.ink2 }}>{c.s}</div>
          </div>
        </div>
      ))}
      <div style={{
        position: "absolute", left: COL.can.x, top: CLI.y, width: COL.can.w, height: CLI.h, boxSizing: "border-box", padding: "18px 22px",
        borderRadius: 22, background: C.surface2, border: `2px solid ${C.line2}`, transform: `scale(${cli})`, display: "flex", alignItems: "center", gap: 16,
      }}>
        <Icon name="users" size={44} color={C.ink2} />
        <div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Sus clientes</div>
          <div style={{ fontFamily: F.body, fontSize: 20, color: C.muted }}>llaman o reciben la llamada</div>
        </div>
      </div>

      <Paso n={1} x={485} y={428} o={pasos[0]} />
      <Paso n={2} x={855} y={300} o={pasos[1]} />
      <Paso n={3} x={1365} y={404} o={pasos[2]} />
      <Paso n={4} x={665} y={826} o={pasos[3]} />

      <Paquete k={DYN_PA} t0={paAt - 0.2} t1={paAt + 0.5} w={66}>{"{ }"}</Paquete>
      <Paquete k={PA_API} t0={apiAt - 0.2} t1={apiAt + 0.4} w={66}>{"{ }"}</Paquete>
      <Paquete k={AG_LINEA} t0={hablaAt} t1={hablaAt + 0.8} w={70}><Wave n={4} h={20} /></Paquete>
      <Paquete k={VUELTA} t0={vuelveAt} t1={vuelveAt + 1.2} w={66}>{"{ }"}</Paquete>
      <Paquete k={CLI_AG} t0={entraAt} t1={entraAt + 0.8} w={70}><Wave n={4} h={20} /></Paquete>
      <Paquete k={VUELTA} t0={casoAt} t1={casoAt + 1.2} w={66}>Aa</Paquete>

      <div style={{
        position: "absolute", left: 460, width: 420, top: 652, textAlign: "center", fontFamily: F.body, fontWeight: 700, fontSize: 22, lineHeight: 1.3,
        color: C.accent, opacity: vuelta,
      }}>
        vuelve el resultado: qué pasó, los datos y el link
      </div>
      <div style={{
        position: "absolute", left: 1430, width: 360, top: 760, fontFamily: F.mono, fontSize: 16, color: C.accent2, opacity: entrante, lineHeight: 1.4,
      }}>
        ENTRANTE: EL CLIENTE LLAMA Y EL AGENTE ATIENDE
      </div>

      <div style={{
        position: "absolute", left: 120, right: 120, top: 862, height: 110, boxSizing: "border-box", padding: "0 32px", borderRadius: 22,
        display: "flex", alignItems: "center", gap: 28, background: "#fff", border: `2px solid ${C.line2}`, boxShadow: shadowCard,
        opacity: bi, transform: `translateY(${(1 - bi) * 20}px)`,
      }}>
        <Icon name="chart" size={46} color={C.accent} />
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink, whiteSpace: "nowrap" }}>Power BI</div>
        <div style={{ fontFamily: F.body, fontSize: 24, color: C.ink2, lineHeight: 1.3 }}>
          El tablero que arma Zennon: llamadas, resultados, minutos y lo que el agente dejó en Dynamics, por cliente.
        </div>
      </div>
      <Pie hoja="3 / 5" fuente="Gris: lo del cliente y lo que arma Zennon. Azul: Atentina. Una entrante empieza en los canales." />
    </AbsoluteFill>
  );
};

// ---------- 4. El modelo de alianza y el tablero (PDF, hoja 4) ----------

const KICK = [
  ["KickStart Esencial", "El CRM en marcha, con el lead llamado apenas entra."],
  ["KickStart Crecimiento", "Más un número que atiende y deja casos en Customer Service."],
  ["KickStart Expansión", "Más campañas de voz y WhatsApp desde Journeys y Field Service."],
] as const;
const KPIS = [
  { n: 1180, fmt: (x: number) => Math.round(x).toLocaleString("es-AR"), t: "llamadas atendidas por el agente" },
  { n: 34, fmt: (x: number) => `${Math.round(x)} %`, t: "fuera del horario de atención" },
  { n: 742, fmt: (x: number) => `${Math.round(x)}`, t: "casos creados en Dynamics por el agente" },
  { n: 4, fmt: (x: number) => `${Math.round(x)} min`, t: "del lead nuevo a la primera llamada (mediana)" },
  { n: 58, fmt: (x: number) => `${Math.round(x)}`, t: "reuniones agendadas para los vendedores" },
];
const RESULTADOS = [
  ["Caso creado", 742], ["Consulta resuelta", 341], ["Reunión agendada", 58], ["Volver a llamar", 44], ["No volver a llamar", 12],
] as const;
const CAMPANAS = [
  ["Leads del sitio", "212", "71 %", "27 %", "398"],
  ["Visitas de mañana", "486", "83 %", "91 %", "612"],
  ["Cuotas por vencer", "320", "64 %", "52 %", "455"],
] as const;
const TCOLS = "1.8fr 1fr 1fr 1fr 1fr";

export const Alianza: React.FC = () => {
  const t = useT();
  const kick = KICK.map((_, i) => usePop(en("a6", "un módulo") - 0.1 + i * 0.15));
  const plus = usePop(en("a6", "en cada KickStart"));
  const nota = useIn(en("a6", "en cada KickStart") + 0.5, 0.5);
  const zennon = useIn(en("a6", "Zennon lo") - 0.1, 0.5);
  const atentina = useIn(AT.a7 - 0.1, 0.5);
  const panelAt = en("a6", "y el cliente");
  const panel = useIn(panelAt, 0.7);
  const k = interpolate(t, [panelAt + 0.5, panelAt + 2.0], [0, 1], { ...CLAMP, easing: EASE });
  const medida = interpolate(t, [en("a7", "y cada llamada"), en("a7", "y cada llamada") + 0.3], [0, 1], CLAMP);
  const fin = AT.a7 + DUR.a7;
  return (
    <AbsoluteFill>
      <Headline eyebrow="El modelo de alianza" text="Un módulo de voz para cada KickStart." accent="El cliente sigue siendo de Zennon." size={46} />

      <div style={{ position: "absolute", left: 120, right: 120, top: 236, display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.25fr", gap: 18 }}>
        {KICK.map(([b, s], i) => (
          <div key={b} style={{
            height: 150, boxSizing: "border-box", padding: "18px 22px", borderRadius: 20, background: "#fbfcfe", border: `2px solid ${C.line2}`,
            transform: `scale(${kick[i]})`,
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 26, color: C.ink, whiteSpace: "nowrap" }}>{b}</div>
            <div style={{ fontFamily: F.body, fontSize: 21, lineHeight: 1.3, color: C.ink2, marginTop: 6 }}>{s}</div>
          </div>
        ))}
        <div style={{
          height: 150, boxSizing: "border-box", padding: "16px 22px", borderRadius: 20, background: `linear-gradient(180deg, ${C.accentSoft}, #fff 85%)`,
          border: `3px solid ${C.accent}`, transform: `scale(${plus})`,
        }}>
          <div style={{ fontFamily: F.mono, fontSize: 15, letterSpacing: "0.08em", color: C.accent }}>PARA TODOS</div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.accent, marginTop: 2, whiteSpace: "nowrap" }}>Módulo de voz Atentina</div>
          <div style={{ fontFamily: F.body, fontSize: 20, lineHeight: 1.3, color: C.ink2, marginTop: 4 }}>Agente, número argentino, conector y tablero de Power BI.</div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, top: 400, fontFamily: F.body, fontSize: 19, color: C.muted, opacity: nota }}>
        Un ejemplo de cómo sumarlo: qué incluye cada paquete lo define Zennon.
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 438, display: "flex", gap: 18 }}>
        <div style={{ flex: 1, opacity: zennon, borderRadius: 16, padding: "12px 22px", background: C.surface2, border: `2px solid ${C.line2}`, fontFamily: F.body, fontSize: 23, color: C.ink2 }}>
          <b style={{ color: C.ink }}>Zennon:</b> diseña el agente, lo conecta con Dynamics y entrega el tablero.
        </div>
        <div style={{ flex: 1, opacity: atentina, borderRadius: 16, padding: "12px 22px", background: C.accentSoft, border: `2px solid ${C.accent}`, fontFamily: F.body, fontSize: 23, color: C.accent2 }}>
          <b>Atentina:</b> pone el número, la voz, la inferencia y el soporte.
        </div>
      </div>

      <div style={{
        position: "absolute", left: 120, top: 522, width: 1680, height: 456, borderRadius: 22, overflow: "hidden", border: `2px solid ${C.line2}`,
        background: "#fff", boxShadow: "0 24px 60px rgba(11,18,32,.14)", opacity: panel, transform: `translateY(${(1 - panel) * 50}px)`,
      }}>
        <div style={{ background: C.ink, color: C.ctaInk, fontFamily: F.mono, fontSize: 19, letterSpacing: "0.05em", padding: "11px 28px", display: "flex", justifyContent: "space-between" }}>
          <span>TABLERO · CLIENTE DE ZENNON</span>
          <span style={{ color: C.accentOnDark }}>EJEMPLO CON DATOS ILUSTRATIVOS · UN MES</span>
        </div>
        <div style={{ background: C.bg2, padding: 18, height: 410, boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", gap: 14 }}>
            {KPIS.map((x) => (
              <div key={x.t} style={{
                flex: 1, background: medida > 0.5 && t < fin + 0.5 ? C.accentSoft : "#fff", border: `2px solid ${medida > 0.5 ? C.accent : C.line}`, borderRadius: 14,
                padding: "10px 18px", height: 112, boxSizing: "border-box",
              }}>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, color: C.accent, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>{x.fmt(x.n * k)}</div>
                <div style={{ fontFamily: F.body, fontSize: 18, lineHeight: 1.2, color: C.ink2, marginTop: 4 }}>{x.t}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 14, height: 248 }}>
            <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 16, padding: "14px 22px", boxSizing: "border-box" }}>
              <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.08em", color: C.muted }}>POR RESULTADO</div>
              {RESULTADOS.map(([n, x]) => (
                <div key={n} style={{ display: "grid", gridTemplateColumns: "200px 1fr 60px", alignItems: "center", gap: 10, height: 38 }}>
                  <span style={{ fontFamily: F.body, fontSize: 20, color: C.ink2, whiteSpace: "nowrap" }}>{n}</span>
                  <div style={{ height: 12, width: `${(x / 742) * 100 * k}%`, borderRadius: 6, background: C.accent }} />
                  <span style={{ fontFamily: F.mono, fontSize: 19, color: C.ink, textAlign: "right" }}>{Math.round(x * k)}</span>
                </div>
              ))}
            </div>
            <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 16, padding: "14px 24px", boxSizing: "border-box" }}>
              <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.08em", color: C.muted }}>SALIENTES POR CAMPAÑA</div>
              <div style={{ display: "grid", gridTemplateColumns: TCOLS, marginTop: 10, paddingBottom: 8, borderBottom: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 700, fontSize: 19, color: C.muted }}>
                <span>Campaña</span><span style={{ textAlign: "right" }}>Contactos</span><span style={{ textAlign: "right" }}>Atendidas</span>
                <span style={{ textAlign: "right" }}>Objetivo</span><span style={{ textAlign: "right" }}>Minutos</span>
              </div>
              {CAMPANAS.map((r) => (
                <div key={r[0]} style={{
                  display: "grid", gridTemplateColumns: TCOLS, alignItems: "center", height: 50, borderBottom: `2px solid ${C.line}`,
                  fontFamily: F.mono, fontSize: 21, color: C.ink, opacity: k,
                }}>
                  <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 21 }}>{r[0]}</span>
                  {r.slice(1).map((c, j) => <span key={j} style={{ textAlign: "right" }}>{c}</span>)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <Pie hoja="4 / 5" fuente="Las cifras del tablero son ilustrativas: muestran qué se mide, no un resultado." />
    </AbsoluteFill>
  );
};

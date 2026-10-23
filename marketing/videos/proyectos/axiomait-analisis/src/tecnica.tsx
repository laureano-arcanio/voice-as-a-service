import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { CodeWindow, Typed } from "../../../src/comun/code";
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
const curva = (a: P, b: P, c: P = { x: (a.x + b.x) / 2, y: a.y }): Curva => ({ a, b, c, d: `M${a.x} ${a.y} Q${c.x} ${c.y} ${b.x} ${b.y}` });

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
      position: "absolute", left: p.x - w / 2, top: p.y - 26, width: w, height: 52, borderRadius: 26, background: bg, opacity: o,
      display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 20px rgba(36,86,230,.3)",
      fontFamily: F.mono, fontSize: 22, color: "#fff",
    }}>{children}</div>
  );
};

// ---------- 3. El producto por dentro (PDF, hoja 3) ----------

type Canal = { icon: "phone" | "wa" | "web"; titulo: string; sub: string; cy: number; frag: string };
const CANALES: Canal[] = [
  { icon: "phone", titulo: "Línea telefónica", sub: "número argentino, 0800", cy: 400, frag: "una llamada" },
  { icon: "wa", titulo: "WhatsApp", sub: "mensajes, audios y llamadas", cy: 580, frag: "un WhatsApp" },
  { icon: "web", titulo: "Link y web", sub: "llamada desde el navegador", cy: 760, frag: "el navegador" },
];
const AG = { x: 640, w: 560, y: 300, h: 560 };
const FILAS = [
  { b: "Escucha", s: "reconocimiento de voz (STT)", frag: "escucha" },
  { b: "Decide", s: "modelo de lenguaje (LLM) con sus reglas", frag: "decide" },
  { b: "Habla", s: "síntesis de voz (TTS), 41 voces", frag: "y habla" },
];
const DER = { x: 1360, w: 440 };
const ENTRADAS = CANALES.map((c) => curva({ x: 520, y: c.cy }, { x: AG.x, y: 580 }));
const AL_PANEL = curva({ x: AG.x + AG.w, y: 400 }, { x: DER.x, y: 400 });
const A_LA_API = curva({ x: AG.x + AG.w, y: 640 }, { x: DER.x, y: 640 });

export const Producto: React.FC = () => {
  const t = useT();
  const canales = CANALES.map((c) => usePop(en("a4", c.frag) - 0.1));
  const llegan = en("a4", "llegan");
  const agente = useIn(llegan - 0.6, 0.6);
  const filas = FILAS.map((f) => en("a4", f.frag));
  const arg = en("a4", "en Argentina");
  const panelAt = en("a4", "Todo queda");
  const apiAt = en("a4", "sale por");
  const panel = usePop(panelAt + 0.4);
  const api = usePop(apiAt + 0.3);
  const sistema = useIn(apiAt + 0.9, 0.5);
  const lineas = useIn(llegan - 0.4, 0.5);
  const salidas = useIn(panelAt, 0.5);
  const hablando = t > AT.a4 && t < AT.a4 + DUR.a4 ? 1 : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="El producto por dentro" text="Un agente, tres canales y una API." accent="La inferencia, en Argentina." size={54} />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {ENTRADAS.map((k, i) => <Link key={i} d={k.d} color={C.accent} opacity={Math.min(lineas, canales[i])} />)}
        <Link d={AL_PANEL.d} color={C.accent} opacity={salidas} />
        <Link d={A_LA_API.d} color={C.accent} opacity={salidas} />
        <Link d={`M${DER.x + DER.w / 2} 748 L${DER.x + DER.w / 2} 850`} color={C.muted} opacity={sistema} />
      </svg>

      {CANALES.map((c, i) => (
        <div key={c.titulo} style={{
          position: "absolute", left: 120, top: c.cy - 62, width: 400, height: 124, boxSizing: "border-box", padding: "0 24px",
          display: "flex", alignItems: "center", gap: 20, borderRadius: 22, background: C.accentSoft, border: `2px solid ${C.accent}`,
          transform: `scale(${canales[i]})`,
        }}>
          <div style={{ width: 64, height: 64, borderRadius: 32, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Icon name={c.icon} size={36} color={C.accent} />
          </div>
          <div>
            <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 30, color: C.accent2 }}>{c.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 20, color: C.ink2, marginTop: 2, whiteSpace: "nowrap" }}>{c.sub}</div>
          </div>
        </div>
      ))}
      <div style={{ position: "absolute", left: 120, width: 400, top: 850, textAlign: "center", fontFamily: F.mono, fontSize: 19, color: C.muted, opacity: lineas }}>
        ENTRANTES Y SALIENTES
      </div>

      {ENTRADAS.map((k, i) => (
        <Paquete key={i} k={k} t0={llegan - 0.1 + i * 0.12} t1={llegan + 0.8 + i * 0.12}><Wave n={4} h={22} /></Paquete>
      ))}

      <div style={{
        position: "absolute", left: AG.x, top: AG.y, width: AG.w, height: AG.h, boxSizing: "border-box", padding: "26px 30px",
        background: "#fff", border: `3px solid ${C.accent}`, borderRadius: 28, boxShadow: shadowCard, opacity: agente,
        transform: `translateY(${(1 - agente) * 24}px)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <AgenteLogo size={84} talk={hablando * 0.5} />
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.accent }}>ATENTINA</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ink }}>El agente</div>
          </div>
        </div>
        {FILAS.map((f, i) => {
          const on = interpolate(t, [filas[i] - 0.1, filas[i] + 0.2, filas[i] + 1.2, filas[i] + 1.6], [0, 1, 1, 0.35], CLAMP);
          const visto = t >= filas[i] - 0.1 ? 1 : 0.35;
          return (
            <div key={f.b} style={{
              marginTop: i === 0 ? 22 : 14, height: 92, boxSizing: "border-box", padding: "12px 22px", borderRadius: 18,
              background: on > 0.5 ? C.accent : C.accentSoft, opacity: Math.max(visto, on),
              transform: `scale(${1 + 0.03 * on})`,
            }}>
              <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 30, color: on > 0.5 ? "#fff" : C.accent2 }}>{f.b}</div>
              <div style={{ fontFamily: F.body, fontSize: 22, color: on > 0.5 ? C.accentSoft : C.ink2 }}>{f.s}</div>
            </div>
          );
        })}
        <div style={{
          position: "absolute", left: 30, right: 30, bottom: 22, borderRadius: 14, padding: "10px 16px", textAlign: "center",
          fontFamily: F.mono, fontSize: 18, letterSpacing: "0.06em",
          background: t > arg ? C.ink : C.surface2, color: t > arg ? C.ctaInk : C.muted,
        }}>
          INFERENCIA PROPIA, EN ARGENTINA
        </div>
      </div>

      <Paquete k={AL_PANEL} t0={panelAt} t1={panelAt + 0.6} w={70}>Aa</Paquete>
      <Paquete k={A_LA_API} t0={apiAt - 0.1} t1={apiAt + 0.5} w={70}>{"{ }"}</Paquete>

      {[
        { k: "PANEL", t: "Conversaciones, resultados, latencia por turno y consumo, por cliente", y: 300, p: panel },
        { k: "API /api/v1", t: "Llamadas, campañas, contactos, reportes y webhooks firmados", y: 540, p: api },
      ].map((b) => (
        <div key={b.k} style={{
          position: "absolute", left: DER.x, top: b.y, width: DER.w, height: 200, boxSizing: "border-box", padding: "24px 28px",
          borderRadius: 24, background: C.accentSoft, border: `3px solid ${C.accent}`, transform: `scale(${b.p})`,
        }}>
          <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent }}>{b.k}</div>
          <div style={{ fontFamily: F.body, fontSize: 27, lineHeight: 1.35, color: C.accent2, marginTop: 10 }}>{b.t}</div>
        </div>
      ))}
      <div style={{
        position: "absolute", left: DER.x, top: 850, width: DER.w, boxSizing: "border-box", padding: "18px 28px", borderRadius: 22,
        background: C.surface2, border: `2px solid ${C.line2}`, opacity: sistema,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Su sistema</div>
        <div style={{ fontFamily: F.body, fontSize: 22, color: C.muted, marginTop: 2 }}>Odoo, n8n, TodoTurnos, otro CRM</div>
      </div>
      <Pie hoja="3 / 6" fuente="Su sistema dispara las llamadas por API y recibe el resultado." />
    </AbsoluteFill>
  );
};

// ---------- 4. El llamador del CRM (PDF, hoja 4) ----------

const NODOS = [
  { x: 120, w: 320, k: "AXIOMA O SU CLIENTE", b: "Odoo / CRM", t: "Lead nuevo o etapa “llamar”: acción automatizada o n8n", frag: "el CRM crea" },
  { x: 580, w: 320, k: "ATENTINA", b: "API", t: "Contacto + campaña de voz: hora, horario, reintentos", frag: "por ápi" },
  { x: 1040, w: 350, k: "ATENTINA", b: "El agente llama", t: "Saluda por el nombre, califica y agenda", frag: "El agente llama" },
  { x: 1530, w: 270, k: "EN SU CELULAR", b: "El lead", t: "Atiende y responde; si no, se reintenta", frag: "califica" },
];
const NY = 370;
const NH = 230;
const FLECHAS = ["1 · POST", "2 · a la hora", "3 · llama"];
const VUELTA = curva({ x: 1215, y: NY + NH }, { x: 280, y: NY + NH }, { x: 748, y: NY + NH + 90 });
const CAMPANA = `{ "channel": "voice",
  "agent_id": "<calificador>",
  "starts_at": "2026-11-03T10:00:00-03:00",
  "window_start": 9, "window_end": 18,
  "callback_url": "https://crm.ejemplo.com/hook",
  "contacts": [{ "external_id": "crm.lead/4821", … }] }`;
const WEBHOOK = `{ "event": "contact.finished",
  "contact": {
    "external_id": "crm.lead/4821",
    "outcome": "Diagnóstico agendado",
    "campos": { "empleados": 25, "dia": "jueves 11 h" },
    "link": "https://app.atentina.com.ar/calls/…" } }`;

export const Llamador: React.FC = () => {
  const t = useT();
  const cita = useIn(AT.a5 - 0.1, 0.6);
  const nodos = NODOS.map((n) => usePop(en("a5", n.frag) - 0.15));
  const apiAt = en("a5", "por ápi");
  const horaAt = en("a5", "con la hora");
  const llamaAt = en("a5", "El agente llama");
  const hookAt = en("a5", "un webhook");
  const flechas = [useIn(apiAt - 0.3, 0.4), useIn(horaAt, 0.4), useIn(llamaAt + 0.2, 0.4)];
  const vuelta = useIn(hookAt - 0.1, 0.5);
  const codeL = useIn(apiAt - 0.2, 0.5);
  const codeR = useIn(hookAt, 0.5);
  const hora = interpolate(t, [horaAt - 0.1, horaAt + 0.3], [0, 1], CLAMP);
  const hablando = t > llamaAt && t < AT.a5 + DUR.a5 ? 1 : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="El caso pedido · el llamador del CRM" text="El CRM decide cuándo, el agente llama" accent="y devuelve el resultado." size={50} />
      <div style={{
        position: "absolute", left: 120, right: 120, top: 236, display: "flex", alignItems: "baseline", gap: 18, opacity: cita,
        borderLeft: `6px solid ${C.accent}`, paddingLeft: 22,
      }}>
        <span style={{ fontFamily: F.display, fontWeight: 700, fontSize: 32, color: C.ink }}>“Quiero un agente que llame a ciertos leads del CRM, en momento determinado.”</span>
        <span style={{ fontFamily: F.body, fontSize: 22, color: C.muted, whiteSpace: "nowrap" }}>Axel, en la demo de voz</span>
      </div>

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {NODOS.slice(0, 3).map((n, i) => (
          <Link key={i} d={`M${n.x + n.w + 6} ${NY + 80} L${NODOS[i + 1].x - 8} ${NY + 80}`} color={i === 0 ? C.muted : C.accent} opacity={flechas[i]} />
        ))}
        <path d={VUELTA.d} fill="none" stroke={C.accent} strokeWidth={4} strokeDasharray="12 10" opacity={vuelta}
          strokeDashoffset={-t * 40} />
      </svg>
      {NODOS.slice(0, 3).map((n, i) => (
        <div key={i} style={{
          position: "absolute", left: n.x + n.w, width: NODOS[i + 1].x - n.x - n.w, top: NY + 30, textAlign: "center",
          fontFamily: F.mono, fontSize: 16, color: i === 0 ? C.muted : C.accent, opacity: flechas[i], whiteSpace: "nowrap",
        }}>{FLECHAS[i]}</div>
      ))}

      {NODOS.map((n, i) => (
        <div key={n.b} style={{
          position: "absolute", left: n.x, top: NY, width: n.w, height: NH, boxSizing: "border-box", padding: "20px 24px", borderRadius: 24,
          background: i === 0 ? C.surface2 : i === 1 ? C.accentSoft : "#fff",
          border: i === 0 || i === 3 ? `2px solid ${C.line2}` : `3px solid ${C.accent}`, boxShadow: shadowCard, transform: `scale(${nodos[i]})`,
        }}>
          <div style={{ fontFamily: F.mono, fontSize: 16, letterSpacing: "0.08em", color: i === 0 || i === 3 ? C.muted : C.accent }}>{n.k}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 6 }}>
            {i === 2 ? <AgenteLogo size={56} talk={hablando * 0.5} /> : null}
            {i === 3 ? <Icon name="phone" size={36} color={C.ink2} /> : null}
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink, whiteSpace: "nowrap" }}>{n.b}</div>
          </div>
          <div style={{ fontFamily: F.body, fontSize: 23, lineHeight: 1.32, color: i === 1 ? C.accent2 : C.ink2, marginTop: 10 }}>{n.t}</div>
        </div>
      ))}

      <Paquete k={curva({ x: 440, y: NY + 80 }, { x: 580, y: NY + 80 })} t0={apiAt - 0.2} t1={apiAt + 0.5} w={70}>{"{ }"}</Paquete>
      <Paquete k={curva({ x: 1390, y: NY + 80 }, { x: 1530, y: NY + 80 })} t0={llamaAt + 0.2} t1={llamaAt + 0.9} w={70}><Wave n={4} h={22} /></Paquete>
      <Paquete k={VUELTA} t0={hookAt + 0.1} t1={hookAt + 1.8} w={70}>{"{ }"}</Paquete>
      <div style={{
        position: "absolute", left: 300, right: 700, top: NY + NH + 58, textAlign: "center", fontFamily: F.body, fontWeight: 700, fontSize: 23,
        color: C.accent, opacity: vuelta,
      }}>
        4 · webhook firmado: resultado, datos capturados y link a la conversación
      </div>

      <CodeWindow tab="POST /api/v1/campaigns · ilustrativo" fontSize={18}
        style={{ position: "absolute", left: 120, top: 712, width: 820, opacity: codeL, transform: `translateY(${(1 - codeL) * 20}px)` }}>
        <Typed text={CAMPANA} a={apiAt - 0.1} b={apiAt + 1.6} t={t} />
        <div style={{
          position: "absolute", left: 14, right: 14, top: 45 + 16 + 27 * 2, height: 27, borderRadius: 6,
          background: "rgba(157,182,255,.16)", opacity: hora,
        }} />
      </CodeWindow>
      <CodeWindow tab="POST crm.ejemplo.com/hook · webhook · ilustrativo" fontSize={18}
        style={{ position: "absolute", left: 980, top: 712, width: 820, opacity: codeR, transform: `translateY(${(1 - codeR) * 20}px)` }}>
        <Typed text={WEBHOOK} a={hookAt + 0.2} b={hookAt + 1.8} t={t} />
      </CodeWindow>
      <Pie hoja="4 / 6" fuente="Ejemplos ilustrativos, abreviados: el lead y los datos son inventados." />
    </AbsoluteFill>
  );
};

// ---------- 5. Voces y naturalidad (PDF, hoja 5) ----------

const VOCES = [
  ["Sofía", "Cálida, clara y cercana", "MUJER"],
  ["Martín", "Grave, sereno y confiable", "HOMBRE"],
  ["Valentina", "Joven, alegre y ágil", "MUJER"],
  ["Lucas", "Joven, cordial y dinámico", "HOMBRE"],
  ["Carolina", "Serena, pausada y formal", "MUJER"],
  ["Tomás", "Claro, formal y atento", "HOMBRE"],
  ["Jimena", "Firme, nítida y profesional", "MUJER"],
  ["Diego", "Cálido, pausado y cercano", "HOMBRE"],
  ["Gabriela", "Madura, segura y cordial", "MUJER"],
  ["+ 32", "28 de mujer y 13 de hombre en total", "SE ESCUCHAN EN EL PANEL"],
] as const;
const PALANCAS = [
  ["La voz adecuada", "pausada para turnos, ágil para ventas"],
  ["El estilo del agente", "frases cortas, una pregunta por vez"],
  ["Apertura pregenerada", "un saludo sin cortes"],
  ["Voz a medida", "entrenada con grabaciones propias"],
] as const;

export const Voces: React.FC = () => {
  const t = useT();
  const chips = VOCES.map((_, i) => usePop(AT.a6 + 0.1 + i * 0.09));
  const confAt = en("a6", "depende");
  const latAt = en("a6", "latencia");
  const palancas = PALANCAS.map((_, i) => useIn(confAt + i * 0.25, 0.5));
  const escala = useIn(latAt - 0.2, 0.6);
  const masAt = en("a7", "Con más");
  // La perilla: al medio, hacia "Responde antes" con "Con menos espera", hacia "Suena más fluida" con "Con más"
  const knob = interpolate(t, [AT.a7 - 0.1, AT.a7 + 0.6, masAt - 0.1, masAt + 0.7, AT.a8 - 0.2, AT.a8 + 0.4], [0.5, 0.12, 0.12, 0.88, 0.88, 0.4],
    { ...CLAMP, easing: EASE });
  const izq = interpolate(t, [AT.a7, AT.a7 + 0.4, masAt, masAt + 0.3], [0.45, 1, 1, 0.45], CLAMP);
  const der = interpolate(t, [masAt, masAt + 0.4], [0.45, 1], CLAMP);
  const honesto = useIn(AT.a8 - 0.1, 0.6);
  const sonando = Math.floor((t - AT.a6) / 0.55) % 9;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Voces y naturalidad" text="41 voces argentinas," accent="y una naturalidad que se configura." size={60} />
      <div style={{ position: "absolute", left: 120, right: 120, top: 250, display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
        {VOCES.map(([n, d, g], i) => {
          const ultimo = i === VOCES.length - 1;
          const activo = !ultimo && t > AT.a6 && t < confAt && sonando === i;
          return (
            <div key={n} style={{
              height: 92, boxSizing: "border-box", padding: "10px 18px", borderRadius: 16, transform: `scale(${chips[i]})`,
              background: ultimo ? C.accentSoft : activo ? C.accent : "#fff", border: `2px solid ${ultimo ? "#c9d7ff" : activo ? C.accent : C.line}`,
              position: "relative",
            }}>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 26, color: activo ? "#fff" : C.ink }}>{n}</div>
              <div style={{ fontFamily: F.body, fontSize: 18, color: activo ? C.accentSoft : C.ink2, whiteSpace: "nowrap" }}>{d}</div>
              <div style={{ position: "absolute", right: 14, top: 12, fontFamily: F.mono, fontSize: 13, color: activo ? C.accentSoft : C.muted }}>
                {activo ? <Wave n={4} h={18} /> : ultimo ? "" : g}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{
        position: "absolute", left: 120, top: 470, width: 960, height: 330, boxSizing: "border-box", padding: "26px 36px", borderRadius: 24,
        background: `linear-gradient(180deg, ${C.bg2}, #fff 75%)`, border: `2px solid ${C.line}`, opacity: escala,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>EL COMPROMISO CON LA LATENCIA</div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14, fontFamily: F.display, fontWeight: 800, fontSize: 34 }}>
          <span style={{ color: C.ink, opacity: izq }}>Responde antes</span>
          <span style={{ color: C.ink, opacity: der }}>Suena más fluida</span>
        </div>
        <div style={{ position: "relative", height: 16, borderRadius: 8, marginTop: 18, background: `linear-gradient(90deg, #9db6ff, ${C.accent})` }}>
          <div style={{
            position: "absolute", top: -12, left: `calc(${knob * 100}% - 20px)`, width: 40, height: 40, borderRadius: 20, background: "#fff",
            border: `5px solid ${C.accent2}`, boxSizing: "border-box", boxShadow: "0 4px 12px rgba(23,64,184,.3)",
          }} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 40, marginTop: 24, fontFamily: F.body, fontSize: 23, lineHeight: 1.35, color: C.ink2 }}>
          <div style={{ opacity: izq }}><b>Menos espera:</b> empieza apenas el otro termina. Para charlas rápidas.</div>
          <div style={{ opacity: der, textAlign: "right" }}><b>Más espera:</b> frases más completas, entonación más pareja.</div>
        </div>
        <div style={{ marginTop: 18, fontFamily: F.mono, fontSize: 17, color: C.accent2 }}>
          EN SU LLAMADA A LA DEMO: 0,87 S DE RESPUESTA PROMEDIO · MÁX. 1,17 S EN 6 TURNOS
        </div>
      </div>

      <div style={{
        position: "absolute", left: 1120, top: 470, width: 680, height: 330, boxSizing: "border-box", padding: "26px 32px", borderRadius: 24,
        background: "#fff", border: `2px solid ${C.line}`, boxShadow: shadowCard, opacity: palancas[0],
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>QUÉ LA HACE SONAR MÁS NATURAL</div>
        {PALANCAS.map(([b, s], i) => (
          <div key={b} style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: i === 0 ? 16 : 12, opacity: palancas[i], borderTop: i ? `2px solid ${C.line}` : "none", paddingTop: i ? 10 : 0 }}>
            <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 27, color: C.accent, whiteSpace: "nowrap" }}>{b}</span>
            <span style={{ fontFamily: F.body, fontSize: 21, color: C.ink2 }}>{s}</span>
          </div>
        ))}
      </div>

      <div style={{
        position: "absolute", left: 120, right: 120, top: 830, height: 140, boxSizing: "border-box", padding: "0 36px", borderRadius: 24,
        display: "flex", alignItems: "center", gap: 40, background: C.okSoft, border: "2px solid #bfe6cf",
        opacity: honesto, transform: `translateY(${(1 - honesto) * 20}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ok, whiteSpace: "nowrap" }}>Natural, pero honesto</div>
        <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.35, color: C.ink2 }}>
          Suena como una persona y habla como la empresa, pero <b>no niega ser una IA</b>: se presenta como asistente y, si le preguntan, lo dice.
        </div>
      </div>
      <Pie hoja="5 / 6" fuente="Latencia: registro de la llamada del 22-oct-2026, medida en el servidor." />
    </AbsoluteFill>
  );
};

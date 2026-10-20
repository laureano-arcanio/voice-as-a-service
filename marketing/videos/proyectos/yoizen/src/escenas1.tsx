import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { CodeWindow, Ok, Typed } from "../../../src/comun/code";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, Icon, Pill, useIn, usePop } from "../../../src/comun/ui";

const Chip: React.FC<{ p: number; children: React.ReactNode; dark?: boolean; style?: React.CSSProperties }> = ({ p, children, dark, style }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 10, borderRadius: 999, padding: "10px 22px", fontFamily: F.mono, fontSize: 24,
    background: dark ? "#16213a" : "#fff", color: dark ? C.ctaInk : C.ink, border: `2px solid ${dark ? "#23304d" : C.line}`,
    transform: `scale(${p})`, ...style,
  }}>
    {children}
  </div>
);

/** 0. Intro oscura: para quién es y qué se integra. */
export const Intro: React.FC = () => {
  const logo = usePop(0.2);
  const title = useIn(0.9, 0.7);
  const chips = [usePop(2.0), usePop(2.4), usePop(2.8), usePop(3.2)];
  const cast = useIn(3.4, 0.8);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.1, 0.5) }}>
        ATENTINA × YOIZEN · INTEGRACIÓN DE VOZ
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 220, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 560 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 400, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 70,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Voz con IA para los agentes<br /><span style={{ color: C.accentOnDark }}>que ya tienen.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 620, display: "flex", justifyContent: "center", gap: 18 }}>
        {["Agentes", "Llamadas", "Transcripción", "Síntesis"].map((x, i) => <Chip key={x} p={chips[i]} dark>{x}</Chip>)}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: -40, display: "flex", justifyContent: "center", alignItems: "flex-end", gap: 50, opacity: cast, transform: `translateY(${(1 - cast) * 120}px)` }}>
        <Person {...CAST.integrador} size={250} pose="laptop" mood="happy" />
        <Mascot size={280} />
        <Person {...CAST.cliente} size={250} pose="phone" mood="happy" />
      </div>
    </AbsoluteFill>
  );
};

const YOIZEN = [
  { icon: "users" as const, t: "Bots no-code" },
  { icon: "store" as const, t: "Orquestador" },
  { icon: "wa" as const, t: "WhatsApp · Web chat" },
  { icon: "phone" as const, t: "IVR · ACD · Asterisk" },
  { icon: "calendar" as const, t: "CRM y tickets" },
];
const ATENTINA = [
  { icon: "phone" as const, t: "Telefonía, números y SIP" },
  { icon: "ear" as const, t: "Reconocimiento de voz" },
  { icon: "users" as const, t: "LLM propio o el suyo" },
  { icon: "speaker" as const, t: "Síntesis de voz · 41 voces" },
  { icon: "web" as const, t: "Agentes, llamadas y campañas" },
  { icon: "clock" as const, t: "Datos y métricas" },
];
const LANES = [
  { y: 430, name: "API de agentes", path: "/api/v1/agents" },
  { y: 600, name: "API de llamadas", path: "/api/v1/calls · /campaigns" },
  { y: 770, name: "API de inferencia", path: "/api/v1/inference" },
];

const Panel: React.FC<{ x: number; eyebrow: string; title: string; rows: { icon: Parameters<typeof Icon>[0]["name"]; t: string }[]; at: number; ours?: boolean }> = ({
  x, eyebrow, title, rows, at, ours,
}) => {
  const p = usePop(at);
  const rs = rows.map((_, i) => useIn(at + 0.3 + i * 0.25, 0.3));
  return (
    <Card style={{
      position: "absolute", left: x, top: 290, width: 500, padding: "24px 28px", transform: `scale(${p})`, transformOrigin: "50% 0%",
      borderColor: ours ? C.accent : C.line2, background: ours ? "#fff" : "#fbfcfe",
    }}>
      <div style={{ fontFamily: F.mono, fontSize: 19, letterSpacing: "0.08em", color: ours ? C.accent : C.muted }}>{eyebrow}</div>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ink, marginBottom: 8 }}>{title}</div>
      {rows.map((r, i) => (
        <div key={r.t} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 0", borderTop: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.ink, opacity: rs[i], transform: `translateX(${(1 - rs[i]) * 18}px)` }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: ours ? C.accentSoft : C.surface2, display: "grid", placeItems: "center" }}>
            <Icon name={r.icon} size={26} color={ours ? C.accent : C.ink2} />
          </div>
          {r.t}
        </div>
      ))}
    </Card>
  );
};

/** 1. Arquitectura: la plataforma de Yoizen queda igual; Atentina suma la voz, conectada por tres APIs. */
export const Arquitectura: React.FC = () => {
  const frame = useCurrentFrame();
  const lanes = LANES.map((_, i) => usePop(7.4 + i * 0.4));
  const keys = useIn(9.2, 0.4);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Arquitectura" text="Su plataforma," accent="más voz administrada." />
      <Panel x={100} eyebrow="SU PLATAFORMA" title="Yoizen" rows={YOIZEN} at={0.5} />
      <Panel x={1320} eyebrow="VOZ ADMINISTRADA" title="Atentina" rows={ATENTINA} at={3.6} ours />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {LANES.map((l, i) => (
          <g key={i} opacity={lanes[i]}>
            <path d={`M600 ${l.y} H1320`} stroke={C.accent} strokeWidth={4} strokeDasharray="3 12" strokeDashoffset={-frame * 2} strokeLinecap="round" />
            <path d={`M600 ${l.y + 14} H1320`} stroke={C.line2} strokeWidth={4} strokeDasharray="3 12" strokeDashoffset={frame * 2} strokeLinecap="round" />
          </g>
        ))}
      </svg>
      {LANES.map((l, i) => (
        <div key={i} style={{
          position: "absolute", left: 960 - 200, top: l.y - 46, width: 400, textAlign: "center", background: "#fff", border: `2px solid ${C.accent}`,
          borderRadius: 18, padding: "12px 10px", boxShadow: shadowCard, transform: `scale(${lanes[i]})`,
        }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink }}>{l.name}</div>
          <div style={{ fontFamily: F.mono, fontSize: 19, color: C.accent }}>{l.path}</div>
        </div>
      ))}
      <div style={{ position: "absolute", left: 660, width: 600, top: 880, textAlign: "center", fontFamily: F.mono, fontSize: 21, color: C.muted, opacity: keys }}>
        HTTPS · una API key por sistema, con alcance
      </div>
    </AbsoluteFill>
  );
};

const AGENT_JSON = `{
  "name": "Atención · voz",
  "definition": {
    "agent": { "name": "Sofía", "voice": "valentina" },
    "objective": { "description": "Resolver consultas" },
    "conversation": {
      "opening": "Hola, te habla Sofía. ¿En qué te ayudo?",
      "rules": ["Tratar de vos", "Frases cortas"]
    },
    "knowledge": "Horarios, medios de pago, …",
    "fields": {
      "documento": { "type": "string", "required": true },
      "motivo": { "type": "string", "required": true }
    }
  }
}`;

// Qué parte del bot va a qué clave del JSON, y cuándo la escribe (s)
const MAP = [
  { t: "Instrucciones", key: "objective · rules", at: 1.9 },
  { t: "Saludo", key: "opening", at: 2.3 },
  { t: "Base de conocimiento", key: "knowledge", at: 3.2 },
  { t: "Datos a tomar", key: "fields", at: 3.7 },
];

/** 2. API de agentes: el bot de Yoizen se publica como agente de voz, versionado. */
export const Agentes: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const bot = usePop(0.3);
  const win = usePop(0.9);
  const created = t > 5.6;
  const agent = usePop(5.7);
  const v2 = t > 7.6;
  const v2p = usePop(7.6);
  const tools = useIn(8.4, 0.4);
  return (
    <AbsoluteFill>
      <Headline eyebrow="API de agentes" text="Cada bot," accent="como agente de voz." />

      {/* El bot, como lo tienen hoy */}
      <Card style={{ position: "absolute", left: 90, top: 300, width: 470, padding: "22px 26px", transform: `scale(${bot})`, transformOrigin: "50% 0%", background: "#fbfcfe", borderColor: C.line2 }}>
        <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>BOT EN YOIZEN</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink, marginBottom: 10 }}>Atención</div>
        {MAP.map((m) => {
          const on = t > m.at && t < m.at + 1.2;
          const done = t > m.at;
          return (
            <div key={m.t} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, margin: "10px 0", padding: "14px 18px", borderRadius: 16,
              border: `2px solid ${on ? C.accent : C.line}`, background: on ? C.accentSoft : "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 24, color: C.ink,
            }}>
              {m.t}
              <span style={{ fontFamily: F.mono, fontSize: 17, color: done ? C.accent : C.line2 }}>→ {m.key}</span>
            </div>
          );
        })}
        <div style={{ fontFamily: F.mono, fontSize: 18, color: C.muted, marginTop: 14 }}>Lo arman sus equipos, sin código</div>
      </Card>

      {/* El pedido */}
      <div style={{ position: "absolute", left: 600, top: 290, width: 800, transform: `scale(${win})`, transformOrigin: "50% 0%" }}>
        <CodeWindow tab="agente.json" method={v2 ? "PUT" : "POST"} path={v2 ? "/api/v1/agents/{id}/definition" : "/api/v1/agents"}
          status={created ? <Ok>{v2 ? "200 OK · v2" : "201 Created · v1"}</Ok> : null} fontSize={20} minHeight={560}>
          <Typed text={AGENT_JSON} a={1.2} b={5.0} t={t} />
        </CodeWindow>
      </div>

      {/* El agente de voz */}
      <div style={{ position: "absolute", left: 1470, top: 330, transform: `scale(${agent})`, transformOrigin: "50% 100%" }}>
        <Mascot size={330} talk={created ? 0.3 + 0.3 * Math.abs(Math.sin(frame / 4)) : 0} />
      </div>
      <div style={{ position: "absolute", left: 1450, top: 690, width: 330, display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
        <Pill bg={C.okSoft} fg={C.ok} style={{ fontSize: 23, transform: `scale(${agent})`, transformOrigin: "left center" }}>
          <Icon name="check" size={24} /> Agente de voz · v1
        </Pill>
        <Pill bg={C.accentSoft} fg={C.accent} style={{ fontSize: 23, transform: `scale(${v2p})`, transformOrigin: "left center" }}>
          <Icon name="clock" size={24} /> Cambio → versión 2
        </Pill>
        <div style={{ fontFamily: F.mono, fontSize: 17, color: C.muted, lineHeight: 1.6, opacity: tools }}>
          GET /api/v1/agents/schema<br />POST /api/v1/agents/validate
        </div>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <path d="M1405 520 L1470 520" stroke={C.accent} strokeWidth={5} strokeDasharray="2 12" strokeLinecap="round" opacity={interpolate(t, [5.4, 5.8], [0, 1], CLAMP)} />
      </svg>
    </AbsoluteFill>
  );
};

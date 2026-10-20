import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, Icon, Pill, useIn, usePop } from "../../../src/comun/ui";

// La definición que se manda: la forma real de POST /api/v1/agents (AgentCreate + Workflow), recortada
const AGENT_JSON = `{
  "name": "Atención",
  "definition": {
    "engine": "assistant",
    "agent": { "name": "Valentina", "voice": "valentina" },
    "objective": { "description": "Atender y registrar cada consulta" },
    "tools": [{ "app": "crm" }],
    "fields": {
      "nombre": { "type": "string", "required": true },
      "motivo": { "type": "string", "required": true },
      "observaciones": { "type": "string" }
    }
  }
}`;

// Lo que devuelve GET /api/v1/calls/{id} (CallDetail), recortado
const RESULT_JSON = `{
  "agent_name": "Atención",
  "outcome": { "label": "Consulta resuelta", "goal": true },
  "fields": [
    { "name": "nombre", "value": "Carolina Pérez" },
    { "name": "motivo", "value": "Actualizar sus datos" },
    { "name": "observaciones",
      "value": "Prefiere que la llamen a la tarde" }
  ],
  "call": { "mode": "entrante", "duration_seconds": 42 },
  "messages": [ … ]
}`;

/** Colorea una línea de JSON: claves, textos, valores y signos. */
const JsonLine: React.FC<{ line: string }> = ({ line }) => {
  const parts: React.ReactNode[] = [];
  const re = /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|\d+)\b/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(line))) {
    if (m.index > last) parts.push(<span key={k++} style={{ color: C.ctaMuted }}>{line.slice(last, m.index)}</span>);
    if (m[1]) {
      parts.push(<span key={k++} style={{ color: m[2] ? C.accentOnDark : "#ffd88a" }}>{m[1]}</span>);
      if (m[2]) parts.push(<span key={k++} style={{ color: C.ctaMuted }}>{m[2]}</span>);
    } else parts.push(<span key={k++} style={{ color: "#5ee49a" }}>{m[3]}</span>);
    last = re.lastIndex;
  }
  if (last < line.length) parts.push(<span key={k++} style={{ color: C.ctaMuted }}>{line.slice(last)}</span>);
  return <div>{parts.length ? parts : " "}</div>;
};

/** Texto que se va escribiendo entre `a` y `b` (s). */
const Typed: React.FC<{ text: string; a: number; b: number; t: number }> = ({ text, a, b, t }) => {
  const n = Math.floor(interpolate(t, [a, b], [0, text.length], CLAMP));
  const shown = text.slice(0, n).split("\n");
  return <>{shown.map((l, i) => <JsonLine key={i} line={l} />)}</>;
};

const Row: React.FC<{ k: string; v: string; p: number }> = ({ k, v, p }) => (
  <div style={{
    display: "grid", gridTemplateColumns: "170px 1fr", gap: 12, padding: "14px 0", borderBottom: `2px solid ${C.line}`,
    fontFamily: F.body, fontSize: 25, opacity: p, transform: `translateX(${(1 - p) * 24}px)`,
  }}>
    <div style={{ color: C.muted }}>{k}</div>
    <div style={{ fontWeight: 600, color: C.ink }}>{v}</div>
  </div>
);

/** 4. API: el integrador define el agente en JSON, lo crea, y después lee el resultado de cada llamada. */
export const Api: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const PART2 = 6.0;
  const second = t >= PART2;
  const win = usePop(0.15);
  const sent = t > 4.3;
  const created = t > 4.7;
  const mascot = usePop(4.8) * (1 - useIn(PART2 - 0.2, 0.3));
  const arrow = useIn(4.5, 0.4) * (1 - useIn(PART2 - 0.2, 0.3));
  const result = usePop(PART2 + 0.3);
  const rows = [useIn(9.7, 0.4), useIn(10.2, 0.4), useIn(10.9, 0.4), useIn(11.4, 0.4)];
  const outcome = usePop(12.0);
  const swap = useIn(PART2 - 0.25, 0.25) * (1 - useIn(PART2, 0.25));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Para desarrolladores" text="Definí el agente en JSON" accent="y crealo por API." out={PART2 - 0.3} />
      <Headline eyebrow="Resultado de cada llamada" text="Datos, observaciones" accent="y cómo terminó." at={PART2 + 0.1} />

      {/* Editor / cliente HTTP */}
      <div style={{ position: "absolute", left: 380, top: 270, width: 940, transform: `scale(${win})`, transformOrigin: "50% 100%", opacity: 1 - swap * 0.7 }}>
        <div style={{ background: C.ink, borderRadius: 28, overflow: "hidden", boxShadow: "0 24px 60px rgba(11,18,32,.25)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "14px 20px", background: "#151d2e" }}>
            {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 14, height: 14, borderRadius: 7, background: c }} />)}
            <div style={{ fontFamily: F.mono, fontSize: 20, color: C.ctaInk, marginLeft: 14, background: "#0b1220", borderRadius: 8, padding: "4px 12px" }}>
              {second ? "respuesta.json" : "agente.json"}
            </div>
          </div>
          {/* Barra del pedido */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 24px", borderBottom: "2px solid #1e2940", fontFamily: F.mono, fontSize: 22 }}>
            <span style={{ background: second ? "#1e3a2a" : "#1d2f63", color: second ? "#5ee49a" : C.accentOnDark, borderRadius: 8, padding: "4px 12px" }}>
              {second ? "GET" : "POST"}
            </span>
            <span style={{ color: C.ctaInk }}>{second ? "/api/v1/calls/{id}" : "/api/v1/agents"}</span>
            <div style={{ flex: 1 }} />
            {second ? (
              <span style={{ color: "#5ee49a" }}>200 OK</span>
            ) : created ? (
              <span style={{ color: "#5ee49a" }}>201 Created</span>
            ) : (
              <span style={{ background: C.accent, color: "#fff", borderRadius: 10, padding: "6px 18px", fontFamily: F.body, fontWeight: 700, transform: `scale(${sent && t < 4.5 ? 0.92 : 1})` }}>
                Enviar
              </span>
            )}
          </div>
          <div style={{ padding: "20px 28px", fontFamily: F.mono, fontSize: 21, lineHeight: 1.55, minHeight: 520, whiteSpace: "pre" }}>
            {second ? <Typed text={RESULT_JSON} a={PART2 + 0.2} b={PART2 + 3.0} t={t} /> : <Typed text={AGENT_JSON} a={0.4} b={3.9} t={t} />}
          </div>
        </div>
      </div>

      {/* Parte 1: el agente creado */}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d="M1330 560 L1430 560" stroke={C.accent} strokeWidth={6} strokeDasharray="2 14" strokeLinecap="round" opacity={arrow} />
      </svg>
      <div style={{ position: "absolute", left: 1460, top: 330, transform: `scale(${mascot})`, transformOrigin: "50% 100%" }}>
        <Mascot size={400} />
      </div>
      <Pill bg={C.okSoft} fg={C.ok} style={{ position: "absolute", left: 1470, top: 750, fontSize: 24, transform: `scale(${mascot})` }}>
        <Icon name="check" size={26} /> Agente “Atención” creado
      </Pill>

      {/* Parte 2: el resultado de la llamada */}
      <Card style={{ position: "absolute", left: 1370, top: 300, width: 500, padding: "26px 30px", transform: `scale(${result})`, transformOrigin: "50% 0%" }}>
        <div style={{ fontFamily: F.mono, fontSize: 20, color: C.accent, letterSpacing: "0.08em" }}>LLAMADA · 0:42</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink, marginTop: 6 }}>Carolina Pérez</div>
        <div style={{ marginTop: 10 }}>
          <Row k="Nombre" v="Carolina Pérez" p={rows[0]} />
          <Row k="Motivo" v="Actualizar sus datos" p={rows[1]} />
          <Row k="Observaciones" v="Prefiere que la llamen a la tarde" p={rows[2]} />
          <Row k="Canal" v="Teléfono" p={rows[3]} />
        </div>
        <Pill bg={C.okSoft} fg={C.ok} style={{ marginTop: 20, fontSize: 26, transform: `scale(${outcome})`, transformOrigin: "left center" }}>
          <Icon name="check" size={28} /> Consulta resuelta
        </Pill>
      </Card>

      <Person {...CAST.integrador} size={400} pose="laptop" mood={created ? "happy" : "neutral"} style={{ position: "absolute", left: 20, top: 700 }} />
      <div style={{ position: "absolute", left: 60, top: 640, opacity: useIn(0.5, 0.4) }}>
        <Pill bg="#fff" fg={C.ink2} style={{ border: `2px solid ${C.line}`, fontFamily: F.mono, fontWeight: 500, fontSize: 20, boxShadow: shadowCard }}>
          Integrador
        </Pill>
      </div>
    </AbsoluteFill>
  );
};

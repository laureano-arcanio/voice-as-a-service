import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { CodeWindow } from "../../../src/comun/code";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, useIn, usePop } from "../../../src/comun/ui";
import { BASE } from "./datos";
import { Nota, PlanBadge, useT } from "./piezas";

const Chip: React.FC<{ p: number; children: React.ReactNode; dark?: boolean; mono?: boolean; style?: React.CSSProperties }> = ({ p, children, dark, mono, style }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 10, borderRadius: 999, padding: "10px 22px", fontFamily: mono ? F.mono : F.body,
    fontWeight: mono ? 500 : 700, fontSize: mono ? 22 : 26, background: dark ? "#16213a" : C.accentSoft, color: dark ? C.ctaInk : C.accent2,
    border: `2px solid ${dark ? "#23304d" : "#cfdbff"}`, transform: `scale(${p})`, opacity: Math.min(1, p * 1.5), whiteSpace: "nowrap", ...style,
  }}>
    {children}
  </div>
);

export const Scope: React.FC<{ children: React.ReactNode; dark?: boolean }> = ({ children, dark }) => (
  <span style={{ fontFamily: F.mono, fontSize: 20, background: dark ? "#1d2f63" : C.accentSoft, color: dark ? C.accentOnDark : C.accent2,
    borderRadius: 8, padding: "2px 10px" }}>{children}</span>
);

/** 0. Intro oscura: qué se integra y la compatibilidad con el SDK de OpenAI. */
export const Intro: React.FC = () => {
  const logo = usePop(0.2);
  const title = useIn(0.8, 0.7);
  const chips = [usePop(2.2), usePop(2.9), usePop(3.4), usePop(4.4)];
  const sdk = useIn(7.0, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.1, 0.5) }}>
        API DE ATENTINA · PARA DESARROLLADORES
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 215, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 460 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 390, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 74,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Agentes, llamadas y voz,<br /><span style={{ color: C.accentOnDark }}>en tu aplicación.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 610, display: "flex", justifyContent: "center", gap: 18 }}>
        {["Agentes de IA", "Llamadas", "Campañas", "LLM · STT · TTS"].map((x, i) => <Chip key={x} p={chips[i]} dark>{x}</Chip>)}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 740, display: "flex", justifyContent: "center", opacity: sdk, transform: `translateY(${(1 - sdk) * 16}px)` }}>
        <div style={{ background: "#0f1a30", border: "2px solid #23304d", borderRadius: 16, padding: "14px 26px", fontFamily: F.mono, fontSize: 26, color: C.ctaInk }}>
          <span style={{ color: "#c4b5fd" }}>OpenAI</span>(base_url=<span style={{ color: "#ffd88a" }}>"…/api/v1/inference"</span>)
          <span style={{ color: "#7d8aa5", marginLeft: 22 }}># compatible con el SDK de OpenAI</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

type Row = { t: string; path: string; at: number };
const PLATAFORMA: Row[] = [
  { t: "Agentes", path: "/agents", at: 3.6 },
  { t: "Llamadas", path: "/calls", at: 4.1 },
  { t: "Contactos", path: "/contacts", at: 4.6 },
  { t: "Campañas", path: "/campaigns", at: 5.1 },
  { t: "Equipo y derivaciones", path: "/team · /handoff-areas", at: 5.7 },
  { t: "Eventos y reportes", path: "/events · report.csv", at: 6.3 },
];
const INFERENCIA: Row[] = [
  { t: "LLM (chat)", path: "POST /chat/completions", at: 8.6 },
  { t: "Transcripción", path: "POST /audio/transcriptions", at: 9.4 },
  { t: "Síntesis · 41 voces argentinas", path: "POST /audio/speech", at: 10.2 },
  { t: "Streaming", path: '"stream": true · "pcm"', at: 12.0 },
];

const ApiCard: React.FC<{ x: number; at: number; eyebrow: string; base: string; scopes: string[]; rows: Row[]; badge: React.ReactNode; badgeAt: number }> = ({
  x, at, eyebrow, base, scopes, rows, badge, badgeAt,
}) => {
  const p = usePop(at);
  const rs = rows.map((r) => useIn(r.at, 0.35));
  const t = useT();
  const b = useIn(badgeAt, 0.5);
  return (
    <Card style={{ position: "absolute", left: x, top: 280, width: 820, padding: "26px 32px", transform: `scale(${p})`, transformOrigin: "50% 0%", borderColor: C.accent }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent }}>{eyebrow}</div>
        <div style={{ display: "flex", gap: 8 }}>{scopes.map((s) => <Scope key={s}>{s}</Scope>)}</div>
      </div>
      <div style={{ fontFamily: F.mono, fontSize: 24, color: C.ink, margin: "10px 0 12px" }}>{base}</div>
      {rows.map((r, i) => {
        const on = t > r.at && t < r.at + 1.0;
        return (
          <div key={r.t} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 14px", borderTop: `2px solid ${C.line}`,
            background: on ? C.accentSoft : "transparent", borderRadius: on ? 10 : 0, opacity: rs[i], transform: `translateX(${(1 - rs[i]) * 16}px)` }}>
            <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 27, color: C.ink }}>{r.t}</span>
            <span style={{ fontFamily: F.mono, fontSize: 20, color: C.accent2 }}>{r.path}</span>
          </div>
        );
      })}
      <div style={{ marginTop: 16, opacity: b }}>{badge}</div>
    </Card>
  );
};

/** 1. Las dos APIs. */
export const Capacidades: React.FC = () => (
  <AbsoluteFill>
    <Headline eyebrow="Dos APIs" text="Plataforma e inferencia," accent="con una API key." />
    <ApiCard x={120} at={0.6} eyebrow="API DE PLATAFORMA" base="/api/v1" scopes={["calls"]} rows={PLATAFORMA} badgeAt={6.8}
      badge={<PlanBadge>Llamadas telefónicas, campañas y equipo, según el plan</PlanBadge>} />
    <ApiCard x={980} at={7.3} eyebrow="API DE INFERENCIA" base="/api/v1/inference" scopes={["llm", "stt", "tts"]} rows={INFERENCIA} badgeAt={12.4}
      badge={<PlanBadge>Todos los planes, Free incluido, con cupo por mes</PlanBadge>} />
  </AbsoluteFill>
);

/** Captura real del panel (backend aislado, datos ficticios), con un acercamiento suave. */
const Captura: React.FC<{ src: string; a: number; b: number; zoom?: [number, number]; origin?: string; style?: React.CSSProperties }> = ({
  src, a, b, zoom = [1, 1.08], origin = "50% 50%", style,
}) => {
  const t = useT();
  const o = interpolate(t, [a, a + 0.4, b - 0.4, b], [0, 1, 1, 0], CLAMP);
  const z = interpolate(t, [a, b], zoom, { ...CLAMP, easing: EASE });
  return (
    <div style={{ position: "absolute", left: 100, top: 270, width: 1100, height: 619, borderRadius: 20, overflow: "hidden", boxShadow: shadowCard,
      border: `2px solid ${C.line}`, opacity: o, ...style }}>
      <Img src={staticFile(src)} style={{ width: 1100, height: 619, transform: `scale(${z})`, transformOrigin: origin }} />
    </div>
  );
};

const SCOPES = [
  { s: "calls", t: "Agentes, llamadas, campañas", at: 4.0 },
  { s: "llm", t: "POST /chat/completions", at: 4.9 },
  { s: "stt", t: "POST /audio/transcriptions", at: 5.6 },
  { s: "tts", t: "POST /audio/speech · /voices", at: 6.2 },
];

/** 2. API key con alcance, URL base y encabezado. */
export const Auth: React.FC = () => {
  const scopes = SCOPES.map((r) => useIn(r.at, 0.35));
  const card = usePop(3.6);
  const win = usePop(9.6);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Autenticación" text="Una key por sistema," accent="con el acceso justo." />
      <Captura src="proyectos/api-desarrolladores/capturas/02-nueva-key.png" a={0.2} b={7.4} zoom={[1.12, 1.55]} origin="50% 50%" />
      <Captura src="proyectos/api-desarrolladores/capturas/03-key-creada.png" a={7.0} b={14.6} zoom={[1.45, 1.75]} origin="50% 50%" />
      <Nota p={useIn(0.8)} style={{ position: "absolute", left: 100, top: 900 }}>Panel › API › Nueva API key · la key, enmascarada</Nota>

      <Card style={{ position: "absolute", left: 1250, top: 270, width: 570, padding: "20px 24px", transform: `scale(${card})`, transformOrigin: "50% 0%" }}>
        <div style={{ fontFamily: F.mono, fontSize: 19, letterSpacing: "0.08em", color: C.accent, marginBottom: 6 }}>ALCANCES</div>
        {SCOPES.map((r, i) => (
          <div key={r.s} style={{ display: "flex", alignItems: "center", gap: 14, padding: "10px 0", borderTop: `2px solid ${C.line}`, opacity: scopes[i] }}>
            <div style={{ width: 80 }}><Scope>{r.s}</Scope></div>
            <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 23, color: C.ink }}>{r.t}</span>
          </div>
        ))}
      </Card>
      <div style={{ position: "absolute", left: 1250, top: 600, width: 570, transform: `scale(${win})`, transformOrigin: "50% 0%" }}>
        <CodeWindow tab="cada pedido" fontSize={18}>
          <div style={{ color: "#7d8aa5" }}># URL base</div>
          <div style={{ color: C.ctaInk }}>{BASE}</div>
          <div style={{ color: C.ctaInk }}>https://app.atentina.com.ar/api/v1</div>
          <div> </div>
          <div><span style={{ color: C.accentOnDark }}>Authorization</span><span style={{ color: C.ctaMuted }}>: Bearer </span><span style={{ color: "#ffd88a" }}>vaas_••••</span></div>
        </CodeWindow>
      </div>
    </AbsoluteFill>
  );
};


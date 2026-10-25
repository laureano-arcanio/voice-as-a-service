import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { CodeWindow } from "../../../src/comun/code";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, Link, useIn, usePop } from "../../../src/comun/ui";
import { Nota, PlanBadge, Scope, useT } from "./piezas";
import { sub } from "./timeline";

const URL_MCP = "https://app.atentina.com.ar/mcp";

// ---------- comunes ----------

/** Ícono propio de cada forma (sin logos de terceros): panel, agente de IA y sistema. */
const FormaIcono: React.FC<{ kind: "panel" | "mcp" | "api"; size?: number; color?: string }> = ({ kind, size = 44, color = C.accent }) => {
  const p = { fill: "none", stroke: color, strokeWidth: 2.2, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  return (
    <svg viewBox="0 0 24 24" width={size} height={size}>
      {kind === "panel" ? (
        <>
          <rect x={3} y={4} width={18} height={14} rx={2.5} {...p} />
          <path d="M8 4v14M11 9h7M11 12.5h5" {...p} />
          <path d="M9 21h6" {...p} />
        </>
      ) : kind === "mcp" ? (
        <>
          <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v7a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4h0A2.5 2.5 0 0 1 4 13.5z" {...p} />
          <path d="M9 10h.01M12 10h.01M15 10h.01" {...p} strokeWidth={3} />
        </>
      ) : (
        <>
          <path d="M8.5 7 4 12l4.5 5M15.5 7 20 12l-4.5 5M13.5 5l-3 14" {...p} />
        </>
      )}
    </svg>
  );
};

const Chip: React.FC<{ p: number; children: React.ReactNode; on?: number }> = ({ p, children, on = 0 }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 14, borderRadius: 999, padding: "14px 28px", fontFamily: F.body, fontWeight: 700, fontSize: 32,
    background: on > 0.5 ? "#1d2f63" : "#16213a", color: C.ctaInk, border: `2px solid ${on > 0.5 ? C.accentOnDark : "#23304d"}`,
    transform: `scale(${p})`, opacity: Math.min(1, p * 1.5), whiteSpace: "nowrap",
  }}>
    {children}
  </div>
);

// ---------- 0. intro ----------

export const Intro: React.FC = () => {
  const t = useT();
  const logo = usePop(0.15);
  const title = useIn(0.4, 0.7);
  const ats = [2.45, 3.4, 4.7];
  const chips = ats.map((a) => usePop(a));
  const FORMAS = [
    { k: "panel" as const, t: "El panel" },
    { k: "mcp" as const, t: "Tu agente de IA", m: "MCP" },
    { k: "api" as const, t: "Tu sistema", m: "API" },
  ];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 140, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 380 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 290, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.2, 0.5) }}>
        DOCUMENTACIÓN · MCP Y API
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 350, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 82,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Tres formas de usar Atentina,<br /><span style={{ color: C.accentOnDark }}>con una sola cuenta.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 640, display: "flex", justifyContent: "center", gap: 26 }}>
        {FORMAS.map((x, i) => (
          <Chip key={x.k} p={chips[i]} on={interpolate(t, [ats[i], ats[i] + 0.2, ats[i] + 1.1, ats[i] + 1.3], [0, 1, 1, 0], CLAMP)}>
            <FormaIcono kind={x.k} size={38} color={C.accentOnDark} />
            {x.t}
            {x.m ? <span style={{ fontFamily: F.mono, fontWeight: 500, fontSize: 22, color: C.accentOnDark, background: "#0f1a30", borderRadius: 8, padding: "2px 10px" }}>{x.m}</span> : null}
          </Chip>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ---------- 1. las tres formas, la misma cuenta ----------

const NODOS = [
  { k: "panel" as const, t: "El panel", s: "Vos, desde el navegador", m: "app.atentina.com.ar", y: 300 },
  { k: "mcp" as const, t: "Tu agente de IA", s: "En español, sin programar", m: "MCP · /mcp", y: 500 },
  { k: "api" as const, t: "Tu sistema", s: "Con una API key", m: "API · /api/v1", y: 700 },
];
const NX = 130, NW = 600, NH = 160;
const CX = 1130, CY = 350, CW = 660, CH = 460;

/** Punto de una cúbica (para que el paquete siga la curva). */
const bez = (t: number, a: number, b: number, c: number, d: number) =>
  (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d;

export const Formas: React.FC = () => {
  const t = useT();
  const nodos = NODOS.map((_, i) => usePop(0.25 + i * 0.2));
  const card = usePop(0.9);
  const links = useIn(1.2, 0.6);
  const rows = [useIn(2.0, 0.4), useIn(2.6, 0.4), useIn(3.3, 0.4)];
  const end = { x: CX, y: CY + CH / 2 };
  return (
    <AbsoluteFill>
      <Headline eyebrow="Panel, MCP y API" text="Las tres hacen lo mismo," accent="con tu cuenta y tu plan." size={62} />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {NODOS.map((n) => {
          const y0 = n.y + NH / 2;
          return <Link key={n.k} d={`M ${NX + NW} ${y0} C ${NX + NW + 200} ${y0}, ${end.x - 200} ${end.y}, ${end.x} ${end.y}`} color={C.accent} opacity={links} width={5} />;
        })}
      </svg>
      {/* Un paquete por forma: el pedido llega a la misma cuenta */}
      {NODOS.map((n, i) => {
        const a = 1.6 + i * 0.45;
        const p = interpolate(t, [a, a + 1.3], [0, 1], { ...CLAMP, easing: EASE });
        if (p <= 0 || p >= 1) return null;
        const y0 = n.y + NH / 2;
        const x = bez(p, NX + NW, NX + NW + 200, end.x - 200, end.x);
        const y = bez(p, y0, y0, end.y, end.y);
        return (
          <div key={n.k} style={{ position: "absolute", left: x - 34, top: y - 22, width: 68, height: 44, borderRadius: 12, background: C.accent, color: "#fff",
            fontFamily: F.mono, fontSize: 22, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 10px 24px rgba(36,86,230,.3)" }}>
            {"{ }"}
          </div>
        );
      })}
      {NODOS.map((n, i) => (
        <Card key={n.k} style={{ position: "absolute", left: NX, top: n.y, width: NW, height: NH, padding: "0 28px", display: "flex", alignItems: "center", gap: 24,
          transform: `scale(${nodos[i]})`, opacity: Math.min(1, nodos[i] * 1.4) }}>
          <div style={{ width: 96, height: 96, borderRadius: 24, background: C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <FormaIcono kind={n.k} size={54} />
          </div>
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ink }}>{n.t}</div>
            <div style={{ fontFamily: F.body, fontSize: 24, color: C.ink2, marginTop: 2 }}>{n.s}</div>
            <div style={{ fontFamily: F.mono, fontSize: 19, color: C.accent2, marginTop: 6 }}>{n.m}</div>
          </div>
        </Card>
      ))}
      <Card style={{ position: "absolute", left: CX, top: CY, width: CW, height: CH, padding: "34px 40px", borderColor: C.accent,
        transform: `scale(${card})`, transformOrigin: "0% 50%", opacity: Math.min(1, card * 1.4) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
          <AgenteLogo size={104} />
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent }}>ATENTINA</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 48, color: C.ink }}>Tu cuenta</div>
          </div>
        </div>
        {[
          "Tus agentes, llamadas y campañas",
          "Los permisos de tu usuario o tu key",
        ].map((r, i) => (
          <div key={r} style={{ display: "flex", alignItems: "center", gap: 16, padding: "20px 0", borderTop: `2px solid ${C.line}`, marginTop: i === 0 ? 26 : 0,
            opacity: rows[i], transform: `translateX(${(1 - rows[i]) * 16}px)` }}>
            <div style={{ width: 12, height: 12, borderRadius: 6, background: C.accent, flexShrink: 0 }} />
            <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 28, color: C.ink }}>{r}</span>
          </div>
        ))}
        <div style={{ borderTop: `2px solid ${C.line}`, paddingTop: 24 }}>
          <PlanBadge p={rows[2]} style={{ fontSize: 26, padding: "10px 18px" }}>Minutos, funciones y topes de tu plan</PlanBadge>
        </div>
      </Card>
    </AbsoluteFill>
  );
};

// ---------- 2. MCP ----------

const ASK = ["Armame un agente para la peluquería que dé turnos", "de martes a sábado, probalo y mostrame", "tres conversaciones."];
const TOOLS = [
  ["get_agent_template", '(template_id: "asistente")'],
  ["create_agent", "  → versión 1"],
  ["test_agent_start", ""],
  ["test_agent_turn", "  × 3 conversaciones"],
];
const USOS = [
  { t: "Armar y probar agentes", tools: "create_agent · test_agent_turn", plan: false },
  { t: "Revisar las llamadas", tools: "list_calls · get_call", plan: false },
  { t: "Lanzar una campaña", tools: "create_campaign · start_campaign", plan: true },
];

export const Mcp: React.FC = () => {
  const t = useT();
  const left = usePop(0.3);
  const agents = [useIn(1.0, 0.4), useIn(1.25, 0.4), useIn(1.5, 0.4), useIn(1.75, 0.4)];
  const oauth = useIn(2.0, 0.5);
  const win = usePop(sub("d3", 1) - 0.1);
  const askP = useIn(sub("d3", 1), 0.5);
  const tools = TOOLS.map((_, i) => useIn(sub("d3", 1) + 1.0 + i * 0.45, 0.3));
  const answer = useIn(sub("d3", 1) + 3.0, 0.4);
  const usoAt = [sub("d3", 2), sub("d3", 2) + 1.6, sub("d3", 3) - 0.1];
  const usos = usoAt.map((a) => usePop(a));
  const sinProg = usePop(sub("d3", 3) + 1.4);
  return (
    <AbsoluteFill>
      <Headline eyebrow="MCP · sin programar" text="Tu agente de IA" accent="maneja tu cuenta." size={62} />
      <Card style={{ position: "absolute", left: 120, top: 270, width: 700, padding: "26px 32px", transform: `scale(${left})`, transformOrigin: "50% 0%", opacity: Math.min(1, left * 1.4) }}>
        <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent }}>CONECTÁ TU AGENTE</div>
        <div style={{ fontFamily: F.mono, fontSize: 27, color: C.ink, background: C.surface2, borderRadius: 12, padding: "12px 18px", margin: "14px 0 18px" }}>{URL_MCP}</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          {["Claude", "ChatGPT", "Cursor", "Claude Code"].map((a, i) => (
            <div key={a} style={{ fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.accent2, background: C.accentSoft, borderRadius: 999, padding: "6px 18px",
              opacity: agents[i], transform: `translateY(${(1 - agents[i]) * 10}px)` }}>{a}</div>
          ))}
        </div>
        <div style={{ fontFamily: F.body, fontSize: 22, color: C.muted, marginTop: 10, opacity: agents[3] }}>u otro agente compatible con MCP</div>
        <div style={{ borderTop: `2px solid ${C.line}`, marginTop: 18, paddingTop: 16, opacity: oauth, display: "grid", gap: 10 }}>
          <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.ink }}>Entrás con tu usuario y aprobás el acceso</div>
          <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink2 }}>87 herramientas; <span style={{ fontFamily: F.mono, fontSize: 21, color: C.accent2 }}>get_plan_tools</span> dice cuáles incluye tu plan</div>
        </div>
      </Card>
      <div style={{ position: "absolute", left: 870, top: 270, width: 930, transform: `scale(${win})`, transformOrigin: "50% 0%", opacity: Math.min(1, win * 1.4) }}>
        <CodeWindow tab="tu agente de IA" fontSize={22} minHeight={392}>
          <div style={{ opacity: askP, color: C.ctaInk, fontFamily: F.body, fontSize: 25, lineHeight: 1.35, whiteSpace: "normal", marginBottom: 12 }}>
            <span style={{ color: "#5ee49a", fontFamily: F.mono }}>{"> "}</span>{ASK.join(" ")}
          </div>
          {TOOLS.map(([n, a], i) => (
            <div key={n} style={{ opacity: tools[i], transform: `translateX(${(1 - tools[i]) * 10}px)` }}>
              <span style={{ color: C.accentOnDark }}>● atentina · </span><span style={{ color: "#ffd88a" }}>{n}</span><span style={{ color: C.ctaMuted }}>{a}</span>
            </div>
          ))}
          <div style={{ opacity: answer, color: C.ctaInk, fontFamily: F.body, fontSize: 24, whiteSpace: "normal", marginTop: 12 }}>
            Creé “Turnos Peluquería” y lo probé en tres conversaciones de texto, sin llamar a nadie.
          </div>
        </CodeWindow>
        <Nota p={answer} style={{ marginTop: 8 }}>Pedido de ejemplo de la documentación · sesión ilustrativa</Nota>
      </div>
      <div style={{ position: "absolute", left: 120, top: 790, right: 120, display: "flex", gap: 22, alignItems: "stretch" }}>
        {USOS.map((u, i) => {
          const on = t > usoAt[i] && t < usoAt[i] + 1.6;
          return (
            <div key={u.t} style={{ flex: 1, background: on ? C.accentSoft : "#fff", border: `2px solid ${on ? C.accent : C.line}`, borderRadius: 20, padding: "14px 22px",
              boxShadow: shadowCard, transform: `scale(${usos[i]})`, opacity: Math.min(1, usos[i] * 1.4) }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontFamily: F.body, fontWeight: 800, fontSize: 28, color: C.ink }}>{u.t}</span>
                {u.plan ? <span style={{ fontFamily: F.mono, fontSize: 16, color: "#a06c00", background: "#fff8e6", border: "2px solid #e8b931", borderRadius: 8, padding: "1px 8px" }}>SEGÚN EL PLAN</span> : null}
              </div>
              <div style={{ fontFamily: F.mono, fontSize: 19, color: C.accent2, marginTop: 4 }}>{u.tools}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", right: 120, top: 92, transform: `scale(${sinProg})`, opacity: Math.min(1, sinProg * 1.4) }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 999, padding: "12px 28px", fontFamily: F.display, fontWeight: 800, fontSize: 32 }}>Sin programar</div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 3. API ----------

type Row = { t: string; path: string; at: number };
const PLATAFORMA: Row[] = [
  { t: "Agentes", path: "/agents", at: 2.0 },
  { t: "Llamadas", path: "/calls", at: 2.6 },
  { t: "Campañas", path: "/campaigns", at: 3.3 },
  { t: "Eventos y webhook", path: "/events · callback_url", at: 3.9 },
];
const INFERENCIA: Row[] = [
  { t: "Lenguaje (LLM)", path: "POST /chat/completions", at: 5.1 },
  { t: "Transcripción", path: "POST /audio/transcriptions", at: 5.9 },
  { t: "Voz · 41 voces argentinas", path: "POST /audio/speech", at: 6.6 },
];

const ApiCard: React.FC<{ x: number; at: number; eyebrow: string; base: string; scopes: string[]; rows: Row[]; extra?: React.ReactNode; badge: React.ReactNode; badgeAt: number }> = ({
  x, at, eyebrow, base, scopes, rows, extra, badge, badgeAt,
}) => {
  const p = usePop(at);
  const rs = rows.map((r) => useIn(r.at, 0.35));
  const t = useT();
  const b = useIn(badgeAt, 0.5);
  return (
    <Card style={{ position: "absolute", left: x, top: 270, width: 820, height: 500, padding: "26px 32px", transform: `scale(${p})`, transformOrigin: "50% 0%",
      opacity: Math.min(1, p * 1.4), borderColor: C.accent }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent }}>{eyebrow}</div>
        <div style={{ display: "flex", gap: 8 }}>{scopes.map((s) => <Scope key={s}>{s}</Scope>)}</div>
      </div>
      <div style={{ fontFamily: F.mono, fontSize: 24, color: C.ink, margin: "10px 0 12px" }}>{base}</div>
      {rows.map((r, i) => {
        const on = t > r.at && t < r.at + 1.0;
        return (
          <div key={r.t} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "13px 14px", borderTop: `2px solid ${C.line}`,
            background: on ? C.accentSoft : "transparent", borderRadius: on ? 10 : 0, opacity: rs[i], transform: `translateX(${(1 - rs[i]) * 16}px)` }}>
            <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 28, color: C.ink }}>{r.t}</span>
            <span style={{ fontFamily: F.mono, fontSize: 20, color: C.accent2 }}>{r.path}</span>
          </div>
        );
      })}
      {extra}
      <div style={{ position: "absolute", left: 32, bottom: 26, opacity: b }}>{badge}</div>
    </Card>
  );
};

export const Api: React.FC = () => {
  const sdk = useIn(7.3, 0.5);
  return (
    <AbsoluteFill>
      <Headline eyebrow="API · para tu sistema" text="Tu sistema, integrado" accent="con una API key." size={62} />
      <ApiCard x={120} at={0.3} eyebrow="API DE PLATAFORMA" base="https://app.atentina.com.ar/api/v1" scopes={["calls"]} rows={PLATAFORMA} badgeAt={4.4}
        badge={<PlanBadge>Llamadas telefónicas y campañas, según el plan</PlanBadge>} />
      <ApiCard x={980} at={4.0} eyebrow="API DE INFERENCIA" base="…/api/v1/inference" scopes={["llm", "stt", "tts"]} rows={INFERENCIA} badgeAt={8.0}
        badge={<PlanBadge>Todos los planes, Free incluido, con cupo por mes</PlanBadge>}
        extra={
          <div style={{ marginTop: 16, opacity: sdk, transform: `translateY(${(1 - sdk) * 12}px)`, background: C.ink, borderRadius: 14, padding: "14px 20px",
            fontFamily: F.mono, fontSize: 21, color: C.ctaInk }}>
            <span style={{ color: "#c4b5fd" }}>OpenAI</span>(base_url=<span style={{ color: "#ffd88a" }}>"…/api/v1/inference"</span>)
            <div style={{ color: "#7d8aa5", marginTop: 4 }}># compatible con el SDK de OpenAI</div>
          </div>
        } />
    </AbsoluteFill>
  );
};

// ---------- 4. cierre ----------

export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const title = useIn(0.4, 0.7);
  const cards = [usePop(1.6), usePop(2.0)];
  const url = useIn(3.6, 0.6);
  const DOCS = [
    { k: "mcp" as const, t: "Conectá tu agente de IA", m: "MCP", path: "/desarrolladores/docs/mcp" },
    { k: "api" as const, t: "Integrá tu sistema", m: "API", path: "/desarrolladores/docs/api" },
  ];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 110, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 340 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 240, textAlign: "center", fontFamily: F.mono, fontSize: 24, letterSpacing: "0.1em", color: C.accentOnDark, opacity: title }}>
        DOCUMENTACIÓN
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 290, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 76, lineHeight: 1.08,
        color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em" }}>
        Elegí la forma <span style={{ color: C.accentOnDark }}>que te sirva.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 440, display: "flex", justifyContent: "center", gap: 30 }}>
        {DOCS.map((d, i) => (
          <div key={d.k} style={{ width: 640, background: "#16213a", border: "2px solid #23304d", borderRadius: 24, padding: "26px 30px",
            transform: `scale(${cards[i]})`, opacity: Math.min(1, cards[i] * 1.4) }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div style={{ width: 72, height: 72, borderRadius: 18, background: "#1d2f63", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <FormaIcono kind={d.k} size={42} color={C.accentOnDark} />
              </div>
              <div>
                <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accentOnDark }}>{d.m}</div>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ctaInk }}>{d.t}</div>
              </div>
            </div>
            <div style={{ fontFamily: F.mono, fontSize: 24, color: C.ctaMuted, marginTop: 16 }}>{d.path}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 710, display: "flex", justifyContent: "center", opacity: url, transform: `translateY(${(1 - url) * 16}px)` }}>
        <div style={{ background: "#fff", color: C.ink, borderRadius: 999, padding: "16px 36px", fontFamily: F.mono, fontSize: 38 }}>
          atentina.com.ar<span style={{ color: C.accent }}>/desarrolladores/docs</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 820, textAlign: "center", fontFamily: F.body, fontSize: 26, color: C.ctaMuted, opacity: useIn(4.6) }}>
        Con un video paso a paso de cada una
      </div>
    </AbsoluteFill>
  );
};

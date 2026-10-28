import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Eyebrow, Icon, Link, useIn, usePop } from "../../../src/comun/ui";
import { Terminal, TERM, useT, type Item } from "./terminal";
import { sub, tramos, type VoId } from "./timeline";

const URL_MCP = "https://app.atentina.com.ar/mcp";
const CMD = `claude mcp add --transport http atentina ${URL_MCP}`;
const DOCS = "https://atentina.com.ar/desarrolladores/docs/mcp";

// ---------- comunes ----------

/** Subtítulos de una línea de locución, abajo al centro. */
const Subs: React.FC<{ id: VoId; dark?: boolean }> = ({ id, dark }) => {
  const t = useT();
  const cur = tramos(id).find(([a, b]) => t >= a && t < b + 0.25);
  if (!cur) return null;
  const [a, b, text] = cur;
  const o = interpolate(t, [a, a + 0.12, b + 0.1, b + 0.25], [0, 1, 1, 0], CLAMP);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{
        background: dark ? "rgba(255,255,255,0.10)" : "rgba(11,18,32,0.86)", color: "#fff", borderRadius: 12, padding: "8px 22px",
        fontFamily: F.body, fontWeight: 600, fontSize: 31, lineHeight: 1.3, whiteSpace: "nowrap",
      }}>
        {text}
      </div>
    </div>
  );
};

const PASOS = ["Cuenta", "Crear", "Probar", "Equipo"] as const;

/** Encabezado de las escenas claras: rótulo + frase en una línea, y los pasos de la demo a la derecha. */
const Header: React.FC<{ eyebrow: string; text: string; accent: string; paso?: number }> = ({ eyebrow, text, accent, paso }) => {
  const p = useIn(0.05, 0.6);
  return (
    <>
      <div style={{ position: "absolute", left: 120, top: 52, opacity: p, transform: `translateY(${(1 - p) * 18}px)` }}>
        <Eyebrow>{eyebrow}</Eyebrow>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 54, lineHeight: 1.1, color: C.ink, marginTop: 10, letterSpacing: "-0.015em", whiteSpace: "nowrap" }}>
          {text} <span style={{ color: C.accent }}>{accent}</span>
        </div>
      </div>
      {paso !== undefined ? (
        <div style={{ position: "absolute", right: 120, top: 62, display: "flex", gap: 10, opacity: p }}>
          {PASOS.map((s, i) => (
            <div key={s} style={{
              fontFamily: F.mono, fontSize: 19, padding: "6px 14px", borderRadius: 999, letterSpacing: "0.04em",
              background: i === paso ? C.accent : i < paso ? C.accentSoft : "#fff", color: i === paso ? "#fff" : i < paso ? C.accent2 : C.muted,
              border: `2px solid ${i === paso ? C.accent : C.line}`,
            }}>
              {i + 1} {s.toUpperCase()}
            </div>
          ))}
        </div>
      ) : null}
    </>
  );
};

// ---------- 1. intro ----------

const Nodo: React.FC<{ x: number; titulo: string; sub: string; at: number; children: React.ReactNode }> = ({ x, titulo, sub: s, at, children }) => {
  const p = usePop(at);
  return (
    <div style={{ position: "absolute", left: x, top: 640, width: 420, textAlign: "center", transform: `scale(${p})`, opacity: Math.min(1, p * 1.4) }}>
      <div style={{ margin: "0 auto", width: 150, height: 150, borderRadius: 34, background: "#16213a", border: "2px solid #23304d", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {children}
      </div>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ctaInk, marginTop: 20 }}>{titulo}</div>
      <div style={{ fontFamily: F.body, fontSize: 25, color: C.ctaMuted, marginTop: 6 }}>{s}</div>
    </div>
  );
};

export const Intro: React.FC = () => {
  const t = useT();
  const logo = usePop(0.1);
  const title = useIn(0.4, 0.7);
  const remate = useIn(sub("m1", 2) - 0.1, 0.5);
  const at = sub("m1", 1);
  const link = useIn(at + 0.5, 0.6);
  // Paquetes "{ }" que van y vuelven por el link (pedido → herramienta → resultado), a ritmo de lectura
  const ida = interpolate(t, [at + 1.2, at + 2.4], [0, 1], { ...CLAMP, easing: EASE });
  const vuelta = interpolate(t, [at + 2.8, at + 4.0], [0, 1], { ...CLAMP, easing: EASE });
  const x0 = 640, x1 = 1280;
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 96, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 280 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 214, textAlign: "center", fontFamily: F.mono, fontSize: 25, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.25, 0.5) }}>
        SERVIDOR MCP · CLAUDE CODE
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 284, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 84,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Administrá Atentina desde Claude Code,<br />
        <span style={{ color: C.accentOnDark, opacity: 0.25 + 0.75 * remate }}>en lenguaje natural.</span>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Link d={`M ${x0 + 130} 715 L ${x1 - 130} 715`} color={C.accentOnDark} opacity={link} width={5} />
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 664, textAlign: "center", fontFamily: F.mono, fontSize: 24, color: C.accentOnDark, opacity: link }}>
        MCP · {URL_MCP.replace("https://", "")}
      </div>
      {[ida, vuelta].map((p, i) => (p > 0 && p < 1 ? (
        <div key={i} style={{
          position: "absolute", top: 740, left: (i === 0 ? x0 + 130 + (x1 - x0 - 260) * p : x1 - 130 - (x1 - x0 - 260) * p) - 34,
          width: 68, height: 44, borderRadius: 12, background: C.accent, color: "#fff", fontFamily: F.mono, fontSize: 22,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {"{ }"}
        </div>
      ) : null))}
      <Nodo x={x0 - 210} titulo="Claude Code" sub="Tu pedido, en lenguaje natural" at={at}>
        <div style={{ fontFamily: F.mono, fontSize: 56, color: C.ctaInk }}>{">_"}</div>
      </Nodo>
      <Nodo x={x1 - 210} titulo="Atentina" sub="Agentes, llamadas, contactos, equipo" at={at + 0.25}>
        <Img src={staticFile("marca/atentina-mark-blanco.svg")} style={{ width: 92 }} />
      </Nodo>
      <Subs id="m1" dark />
    </AbsoluteFill>
  );
};

// ---------- 2. grupos de herramientas ----------

// Grupos y cantidades de app/mcp/catalog.py (landing/src/data/mcp-tools.json, 25-oct-2026): 87 sin `inference`
const GRUPOS: { t: string; n: number; tools: string[]; plan?: boolean }[] = [
  { t: "Cuenta y plan", n: 8, tools: ["get_plan_tools", "whoami", "get_usage"] },
  { t: "Agentes", n: 19, tools: ["create_agent", "update_agent_definition", "test_agent_turn"] },
  { t: "Llamadas", n: 12, tools: ["list_calls", "get_call", "start_call"] },
  { t: "Link para llamar", n: 5, tools: ["create_call_link", "get_call_link", "update_call_link"], plan: true },
  { t: "WhatsApp", n: 6, tools: ["list_whatsapp_accounts", "set_whatsapp_routes", "create_whatsapp_template"], plan: true },
  { t: "Contactos", n: 11, tools: ["upsert_contacts", "import_contacts", "list_contacts"], plan: true },
  { t: "Campañas", n: 14, tools: ["create_campaign", "start_campaign", "get_campaign_stats"], plan: true },
  { t: "Equipo y derivaciones", n: 12, tools: ["create_team_member", "create_handoff_area", "list_events"], plan: true },
];

export const Grupos: React.FC = () => {
  const a = sub("m2", 1);
  const span = sub("m2", 2) + (tramos("m2")[2][1] - sub("m2", 2)) * 0.8 - a;
  const pops = GRUPOS.map((_, i) => usePop(a - 0.3 + (span * i) / GRUPOS.length));
  const nota = useIn(a + span + 0.3, 0.5);
  return (
    <AbsoluteFill>
      <Header eyebrow="Capacidades" text="87 herramientas en ocho grupos," accent="según tu plan." />
      <div style={{ position: "absolute", left: 120, right: 120, top: 236, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24 }}>
        {GRUPOS.map((g, i) => (
          <div key={g.t} style={{
            background: "#fff", border: `2px solid ${C.line}`, borderRadius: 24, boxShadow: shadowCard, padding: "24px 26px", height: 262,
            transform: `scale(${pops[i]})`, opacity: Math.min(1, pops[i] * 1.4),
          }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
              <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 29, color: C.ink }}>{g.t}</div>
              <div style={{ fontFamily: F.mono, fontSize: 30, color: C.accent }}>{g.n}</div>
            </div>
            <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              {g.tools.map((n) => (
                <div key={n} style={{ fontFamily: F.mono, fontSize: 19, color: C.ink2, background: C.surface2, borderRadius: 8, padding: "4px 10px", alignSelf: "flex-start" }}>{n}</div>
              ))}
            </div>
            <div style={{ fontFamily: F.mono, fontSize: 17, color: g.plan ? C.muted : "transparent", marginTop: 12 }}>según el plan</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 842, textAlign: "center", fontFamily: F.body, fontSize: 27, color: C.ink2, opacity: nota }}>
        <span style={{ fontFamily: F.mono, color: C.accent }}>get_plan_tools</span> dice qué incluye tu plan; fuera del plan, la herramienta responde{" "}
        <span style={{ fontFamily: F.mono, color: C.accent }}>feature_not_in_plan</span>.
      </div>
      <Subs id="m2" />
    </AbsoluteFill>
  );
};

// ---------- 3. instalar ----------

// docs/MCP_HERRAMIENTAS.md y docs/features/MCP.md (transporte, URL, auth)
const DATOS_INSTALAR: [string, string, string][] = [
  ["Transporte", "Streamable HTTP", "servidor remoto: no se instala nada"],
  ["URL", "app.atentina.com.ar/mcp", "la misma para Claude, ChatGPT y Cursor"],
  ["Acceso", "OAuth 2.1", "o una API key con el alcance mcp"],
];

const DatoInstalar: React.FC<{ k: string; v: string; extra: string; at: number }> = ({ k, v, extra, at }) => {
  const p = usePop(at);
  return (
    <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 22, boxShadow: shadowCard, padding: "22px 28px", transform: `scale(${p})`, opacity: Math.min(1, p * 1.4) }}>
      <Eyebrow>{k}</Eyebrow>
      <div style={{ fontFamily: F.mono, fontSize: 30, color: C.ink, marginTop: 10, whiteSpace: "nowrap" }}>{v}</div>
      <div style={{ fontFamily: F.body, fontSize: 24, color: C.muted, marginTop: 6 }}>{extra}</div>
    </div>
  );
};

export const Instalar: React.FC = () => {
  const items: Item[] = [
    { k: "cmd", at: 0.5, dur: 1.7, text: CMD },
    { k: "out", at: 2.6, lines: [`Added HTTP MCP server atentina with URL: ${URL_MCP} to local config`, "File modified: /home/dev/.claude.json [project: /home/dev/mi-proyecto]"] },
    { k: "cmd", at: 3.7, dur: 0.5, text: "claude mcp list" },
    { k: "out", at: 4.5, lines: ["Checking MCP server health…", ""] },
    { k: "out", at: 5.2, lines: [`atentina: ${URL_MCP} (HTTP) - ! Needs authentication`], color: TERM.YELLOW },
  ];
  return (
    <AbsoluteFill>
      <Header eyebrow="Instalación · 1 de 2" text="Un comando en la terminal" accent="agrega el servidor." />
      <Terminal items={items} claude={false} style={{ height: 470 }} cam={[[0.3, 1, 0, 0], [0.9, 1.32, 0, 0], [2.4, 1.32, 0, 0], [3.2, 1, 0, 0]]} />
      <div style={{ position: "absolute", left: 120, right: 120, top: 700, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24 }}>
        {DATOS_INSTALAR.map(([k, v, extra], i) => <DatoInstalar key={k} k={k} v={v} extra={extra} at={2.6 + i * 0.35} />)}
      </div>
      <Subs id="m3" />
    </AbsoluteFill>
  );
};

// ---------- 4. autenticar ----------

const MenuMcp: React.FC = () => (
  <div style={{ border: "2px solid #3a4763", borderRadius: 10, padding: "10px 18px", marginTop: 12, color: TERM.TXT }}>
    <div style={{ fontWeight: 600 }}>Manage MCP servers</div>
    <div style={{ color: TERM.DIM }}>1 server</div>
    <div style={{ marginTop: 8 }}><span style={{ color: C.accentOnDark }}>❯ atentina</span> <span style={{ color: TERM.YELLOW }}>· △ needs authentication</span><span style={{ color: TERM.DIM }}> · Enter to view details</span></div>
  </div>
);

const DetalleMcp: React.FC = () => (
  <div style={{ border: "2px solid #3a4763", borderRadius: 10, padding: "10px 18px", marginTop: 12, color: TERM.TXT }}>
    <div style={{ fontWeight: 600 }}>Atentina MCP Server</div>
    <div><span style={{ color: TERM.DIM }}>Status: </span><span style={{ color: TERM.YELLOW }}>△ needs authentication</span></div>
    <div><span style={{ color: TERM.DIM }}>URL: </span>{URL_MCP}</div>
    <div style={{ marginTop: 8, color: C.accentOnDark }}>❯ 1. Authenticate</div>
    <div style={{ color: TERM.DIM }}>{"  2. Disable"}</div>
  </div>
);

const CAN_DO = [
  "Ver y editar tus agentes, y probarlos por texto.",
  "Ver las llamadas y conversaciones, con sus transcripciones.",
  "Cargar contactos y armar campañas (las inicia solo si se lo confirmás).",
  "Configurar el equipo, las derivaciones y WhatsApp.",
];

const Campo: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ marginTop: 14 }}>
    <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 19, color: C.ink }}>{label}</div>
    <div style={{ marginTop: 6, border: `1.5px solid ${C.line2}`, borderRadius: 8, padding: "8px 12px", fontFamily: F.body, fontSize: 20, color: C.ink, height: 26, lineHeight: "26px" }}>{value}</div>
  </div>
);

const Boton: React.FC<{ children: React.ReactNode; primary?: boolean; press?: number; style?: React.CSSProperties }> = ({ children, primary, press = 0, style }) => (
  <div style={{
    background: primary ? (press > 0 ? C.accent2 : C.accent) : "#fff", color: primary ? "#fff" : C.ink, border: primary ? "none" : `1.5px solid ${C.line2}`,
    borderRadius: 8, padding: "10px 18px", fontFamily: F.body, fontWeight: 700, fontSize: 20, textAlign: "center", transform: `scale(${1 - 0.04 * press})`, ...style,
  }}>
    {children}
  </div>
);

/** El navegador con el login y el consentimiento del panel (recreación de web/src/features/{auth,oauth}). */
const Navegador: React.FC<{ a: number; consent: number; click: number; b: number }> = ({ a, consent, click, b }) => {
  const t = useT();
  const p = interpolate(t, [a, a + 0.5, b, b + 0.4], [0, 1, 1, 0], { ...CLAMP, easing: EASE });
  if (p <= 0) return null;
  const email = "dev@ferreteria-ejemplo.com.ar";
  const n = Math.floor(interpolate(t, [a + 0.5, a + 1.3], [0, email.length], CLAMP));
  const login = t < consent;
  const pressLogin = interpolate(t, [consent - 0.35, consent - 0.2, consent - 0.05], [0, 1, 0], CLAMP);
  const pressOk = interpolate(t, [click, click + 0.15, click + 0.3], [0, 1, 0], CLAMP);
  const ring = interpolate(t, [click - 0.6, click - 0.3, click + 0.3, click + 0.5], [0, 1, 1, 0], CLAMP);
  return (
    <div style={{
      position: "absolute", left: 1000, top: 236, width: 780, height: 690, background: C.bg2, borderRadius: 18, overflow: "hidden",
      boxShadow: "0 30px 70px rgba(11,18,32,.35)", border: `2px solid ${C.line}`, opacity: p, transform: `translateX(${(1 - p) * 80}px)`,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", background: "#fff", borderBottom: `2px solid ${C.line}` }}>
        {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />)}
        <div style={{ flex: 1, marginLeft: 10, background: C.surface2, borderRadius: 999, padding: "5px 16px", fontFamily: F.mono, fontSize: 17, color: C.ink2, whiteSpace: "nowrap", overflow: "hidden" }}>
          {login ? "app.atentina.com.ar/login?next=/oauth/consent…" : "app.atentina.com.ar/oauth/consent?client_id=…"}
        </div>
      </div>
      <div style={{ padding: "26px 60px" }}>
        <div style={{ display: "flex", justifyContent: "center" }}><Img src={staticFile("marca/atentina-logo.svg")} style={{ height: 40 }} /></div>
        <div style={{ marginTop: 20, background: "#fff", border: `1.5px solid ${C.line}`, borderRadius: 14, padding: "22px 28px", boxShadow: shadowCard }}>
          {login ? (
            <>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Ingresá a tu cuenta</div>
              <Campo label="Email" value={email.slice(0, n)} />
              <Campo label="Clave" value={t > a + 1.4 ? "••••••••••" : ""} />
              <Boton primary press={pressLogin} style={{ marginTop: 22 }}>Ingresar</Boton>
            </>
          ) : (
            <>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink }}>Conectar Claude Code</div>
              <div style={{ fontFamily: F.body, fontSize: 16, color: C.muted, marginTop: 4 }}>Vuelve a <span style={{ fontFamily: F.mono }}>localhost</span></div>
              <div style={{ fontFamily: F.body, fontSize: 19, color: C.ink, marginTop: 14, lineHeight: 1.35 }}>
                Claude Code va a poder usar tu cuenta de Atentina (Ferretería Ejemplo) como vos:
              </div>
              {CAN_DO.map((c) => (
                <div key={c} style={{ display: "flex", gap: 8, alignItems: "flex-start", fontFamily: F.body, fontSize: 18, color: C.ink2, marginTop: 7, lineHeight: 1.3 }}>
                  <div style={{ flexShrink: 0, marginTop: 1 }}><Icon name="check" size={20} color={C.ok} /></div>{c}
                </div>
              ))}
              <div style={{ fontFamily: F.body, fontSize: 15, color: C.muted, marginTop: 12, lineHeight: 1.35 }}>
                Todo dentro de lo que incluye tu plan. Podés desconectarlo cuando quieras desde Desarrolladores → Agentes conectados.
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 16 }}>
                <Boton>Cancelar</Boton>
                <Boton primary press={pressOk} style={{ boxShadow: `0 0 0 ${6 * ring}px rgba(36,86,230,${0.35 * ring})` }}>Permitir acceso</Boton>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export const Autenticar: React.FC = () => {
  const items: Item[] = [
    { k: "user", at: 0.5, dur: 0.4, text: "/mcp" },
    { k: "node", at: 1.3, until: 2.8, node: <MenuMcp /> },
    { k: "node", at: 2.8, until: 4.1, node: <DetalleMcp /> },
    { k: "out", at: 4.1, lines: ["", "Authenticating with atentina…", "A browser window will open for authentication."] },
    { k: "out", at: 8.5, lines: ["", "Authentication successful. Connected to atentina."], color: TERM.GREEN },
  ];
  return (
    <AbsoluteFill>
      <Header eyebrow="Instalación · 2 de 2" text="Autenticá con tu usuario," accent="por OAuth." />
      <Terminal items={items} />
      <Navegador a={4.3} consent={6.1} click={7.7} b={8.2} />
      <Subs id="m4" />
    </AbsoluteFill>
  );
};

// ---------- 5 a 8. demo ----------

const Acelerado: React.FC = () => (
  <div style={{ fontFamily: F.mono, fontSize: 16, color: C.ink, background: C.accentOnDark, borderRadius: 999, padding: "3px 12px", letterSpacing: "0.06em" }}>
    ACELERADO
  </div>
);

export const Cuenta: React.FC = () => {
  const items: Item[] = [
    { k: "user", at: 0.3, dur: 1.2, text: "¿Qué incluye mi plan y qué herramientas tengo disponibles?" },
    { k: "tool", at: 1.9, name: "whoami", done: 2.4, result: ['{"email": "dev@ferreteria-ejemplo.com.ar", "role": "client", "client_name": "Ferretería Ejemplo", …}'], more: 3 },
    {
      k: "tool", at: 2.8, name: "get_plan_tools", done: 3.5, hl: [3.0, 5.6], more: 96, result: [
        '{"plan": "Sucursal", "free": false,',
        ' "tools": {"available": ["get_plan_tools", "whoami", "get_plan_features", …],',
        '  "unavailable": [], "needs_oauth": [], "needs_api_key": ["transcribe_audio", …]},',
        ' "usage": {"inbound": {"used_minutes": 312.5, "limit_minutes": 1200, …}, …}, …}',
      ],
    },
    { k: "say", at: 5.6, dur: 1.4, text: "Estás en el plan Sucursal de Ferretería Ejemplo: tenés 87 herramientas habilitadas (las 3 de inferencia piden API key). Este mes usaste 312 de 1.200 minutos entrantes." },
  ];
  return (
    <AbsoluteFill>
      <Header eyebrow="Demo · Cuenta" text="Claude mira el plan" accent="antes de proponer." paso={0} />
      <Terminal items={items} cam={[[3.2, 1, 0, 420], [3.8, 1.14, 0, 420], [5.3, 1.14, 0, 420], [5.9, 1, 0, 420]]} />
      <Subs id="m5" />
    </AbsoluteFill>
  );
};

export const Crear: React.FC = () => {
  const items: Item[] = [
    { k: "user", at: 0.2, dur: 1.3, text: "Creá un agente de atención al cliente para la ferretería: lunes a sábado de 8 a 19, envíos en el día a zona sur." },
    { k: "tool", at: 1.9, name: "list_agent_templates", done: 2.2, result: ['[{"id": "asistente", "engine": "classic", "agent": "Sofía, asistente virtual de la empresa, en Argentina", "voice": "sofia", …}]'] },
    { k: "tool", at: 2.6, name: "get_agent_template", args: 'template_id: "asistente"', done: 2.9, result: ['{"id": "asistente", "engine": "classic", "agent": {"name": "Sofía", "voice": "sofia", …}, …}'], more: 74 },
    { k: "tool", at: 3.5, name: "validate_agent_definition", args: "definition: {…}", done: 3.9, hl: [3.9, 4.9], result: ['{"valid": true, "errors": []}'] },
    {
      k: "tool", at: 4.4, name: "create_agent", args: 'name: "Atención al cliente", definition: {…}', done: 4.9, hl: [5.0, 6.8], result: [
        '{"id": "7c1e4f2a-…", "name": "Atención al cliente", "slug": "atencion-al-cliente",',
        ' "version": 1, "engine": "classic", "voice": "sofia", "archived": false, …}',
      ],
    },
    { k: "say", at: 6.4, dur: 1.4, text: "Listo: creé Atención al cliente (versión 1, voz sofia) desde la plantilla asistente, con los horarios y los envíos en la base de conocimiento. ¿Lo pruebo?" },
  ];
  return (
    <AbsoluteFill>
      <Header eyebrow="Demo · Crear" text="Un agente nuevo," accent="desde la plantilla." paso={1} />
      <Terminal items={items} badge={<Acelerado />} />
      <Subs id="m6" />
    </AbsoluteFill>
  );
};

export const Probar: React.FC = () => {
  const items: Item[] = [
    { k: "user", at: 0.2, dur: 0.7, text: "Probalo: preguntá por envíos a Quilmes." },
    { k: "tool", at: 1.2, name: "test_agent_start", args: 'agent_id: "7c1e4f2a-…"', done: 1.6, result: ['{"conversation_id": "c93b0d51-…", "message": "Hola, gracias por comunicarte. Te habla Sofía, la asistente virtual. ¿En qué te puedo ayudar?", …}'] },
    {
      k: "tool", at: 2.3, name: "test_agent_turn", args: 'conversation_id: "c93b0d51-…", message: "¿Hacen envíos a Quilmes en el día?"', done: 3.0, result: [
        '{"message": "Sí, hacemos envíos en el día a toda la zona sur, Quilmes incluido. ¿Te ayudo con algo más?",',
        ' "state": {"fields": {"consulta": "Envíos en el día a Quilmes"}, …}, "status": "active"}',
      ],
    },
    {
      k: "tool", at: 4.0, name: "test_agent_turn", args: 'conversation_id: "c93b0d51-…", message: "No, con eso me alcanza, gracias."', done: 4.7, hl: [4.9, 7.4], result: [
        '{"message": "Gracias por comunicarte, que tengas un buen día.",',
        ' "state": {"fields": {"consulta": "Envíos en el día a Quilmes", "resuelta": true}, …},',
        ' "next_objective": null, "status": "completed"}',
      ],
    },
    { k: "say", at: 7.0, dur: 1.2, text: "La prueba terminó bien: respondió con la base de conocimiento y tomó la consulta y resuelta: true. No llamó a nadie ni gastó minutos." },
  ];
  return (
    <AbsoluteFill>
      <Header eyebrow="Demo · Probar" text="Una conversación de prueba," accent="por texto." paso={2} />
      <Terminal items={items} cam={[[5.0, 1, 0, 520], [5.6, 1.12, 0, 520], [7.0, 1.12, 0, 520], [7.6, 1, 0, 520]]} />
      <Subs id="m7" />
    </AbsoluteFill>
  );
};

export const Equipo: React.FC = () => {
  const items: Item[] = [
    { k: "user", at: 0.2, dur: 1.3, text: "Sumá a Laura Gómez al equipo y creá un área Ventas, de lunes a viernes de 9 a 18, para presupuestos grandes." },
    { k: "tool", at: 1.9, name: "create_team_member", args: 'name: "Laura Gómez", phone: "+5491155551234"', done: 2.4, result: ['{"id": "e2a90f17-…", "name": "Laura Gómez", "phone": "+5491155551234", "whatsapp": null, "active": true, …}'] },
    {
      k: "tool", at: 3.1, name: "create_handoff_area", args: 'name: "Ventas", member_ids: ["e2a90f17-…"], schedule: {…}', done: 3.7, hl: [3.8, 6.6], result: [
        '{"name": "Ventas", "description": "Presupuestos y compras grandes", "member_ids": ["e2a90f17-…"],',
        ' "strategy": "sequential", "ring_seconds": 20, "schedule_text": "de lunes a viernes de 09:00 a 18:00",',
        ' "open_now": true, "fallback": "take_message", "on_person_hangup": "resume", …}',
      ],
    },
    { k: "say", at: 6.4, dur: 1.4, text: "Listo: Laura está en el equipo y el área Ventas atiende de lunes a viernes de 9 a 18. Si nadie atiende, el agente toma el mensaje." },
  ];
  return (
    <AbsoluteFill>
      <Header eyebrow="Demo · Equipo" text="Derivación a personas," accent="con su horario." paso={3} />
      <Terminal items={items} badge={<Acelerado />} />
      <Subs id="m8" />
    </AbsoluteFill>
  );
};

// ---------- 9. cierre ----------

const VERBOS = ["consultar", "crear", "configurar", "probar", "administrar"];

export const Cierre: React.FC = () => {
  const title = useIn(0.3, 0.7);
  const vs = VERBOS.map((_, i) => usePop(sub("m9", 0) + 1.6 + i * 0.45));
  const docs = useIn(sub("m9", 2) + 0.2, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, textAlign: "center", opacity: title }}>
        <Eyebrow color={C.accentOnDark}>TL;DR</Eyebrow>
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 176, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 80,
        lineHeight: 1.1, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Una sola integración,<br /><span style={{ color: C.accentOnDark }}>en lenguaje natural.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 420, display: "flex", justifyContent: "center", gap: 18 }}>
        {VERBOS.map((v, i) => (
          <div key={v} style={{
            fontFamily: F.body, fontWeight: 700, fontSize: 32, color: C.ctaInk, background: "#16213a", border: "2px solid #23304d",
            borderRadius: 999, padding: "12px 28px", transform: `scale(${vs[i]})`, opacity: Math.min(1, vs[i] * 1.4),
          }}>
            {v}
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 560, display: "flex", flexDirection: "column", alignItems: "center", opacity: docs, transform: `translateY(${(1 - docs) * 16}px)` }}>
        <div style={{ fontFamily: F.mono, fontSize: 22, letterSpacing: "0.08em", color: C.ctaMuted }}>DOCUMENTACIÓN</div>
        <div style={{ marginTop: 14, fontFamily: F.mono, fontSize: 42, color: "#fff", background: "#16213a", border: `2px solid ${C.accentOnDark}`, borderRadius: 18, padding: "16px 34px" }}>
          {DOCS}
        </div>
        <div style={{ marginTop: 22, fontFamily: F.mono, fontSize: 22, color: C.ctaMuted }}>{CMD}</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 870, display: "flex", justifyContent: "center", opacity: docs }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 170 }} />
      </div>
      <Subs id="m9" dark />
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { CodeWindow } from "../../../src/comun/code";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, useIn, usePop } from "../../../src/comun/ui";
import { Code, IconoCodigo, Mono, Nota, PlanBadge, useT } from "./piezas";
import { sub } from "./timeline";

// ---------- 4. el endpoint de ejemplo ----------

// examples/agente-externo/server.py, en la versión acortada de la página (sin el chequeo de la key)
const SERVER = `PROMPT = """Sos Sofía, la recepcionista de Acme. Hablás por teléfono: respuestas cortas,
sin listas ni emojis. Cuando la persona se despide, despedite y llamá a end_call."""

app = FastAPI()
llm = AsyncOpenAI()  # tu LLM: OpenAI o cualquiera compatible

@app.post("/v1/chat/completions")
async def chat(request: Request, x_atentina_from: str = Header("")):
    body = await request.json()
    messages = [{"role": "system", "content": f"{PROMPT}\\nLlama: {x_atentina_from}."},
                *body["messages"]]
    stream = await llm.chat.completions.create(
        model="gpt-4.1-mini", messages=messages, tools=body.get("tools"), stream=True)

    async def events():
        async for chunk in stream:
            yield f"data: {chunk.model_dump_json(exclude_none=True)}\\n\\n"
        yield "data: [DONE]\\n\\n"

    return StreamingResponse(events(), media_type="text/event-stream")`;

export const Ejemplo: React.FC = () => {
  const win = usePop(0.2);
  const side = usePop(0.9);
  const rows = [useIn(1.2, 0.4), useIn(sub("t5", 1) - 0.2, 0.4), useIn(sub("t5", 1) + 1.0, 0.4), useIn(sub("t5", 1) + 2.2, 0.4)];
  const h1 = sub("t5", 0) + 0.4;
  const h2 = sub("t5", 1);
  const LADO = [
    "Antepone su prompt",
    "Le pasa la conversación y las herramientas a su LLM",
    "Devuelve el stream tal cual",
    "El resto es tuyo: tus herramientas, tus datos, tu framework",
  ];
  return (
    <AbsoluteFill>
      <Headline eyebrow="Un endpoint de ejemplo" text="Un servidor mínimo," accent="en Python." size={62} />
      <div style={{ position: "absolute", left: 100, top: 250, width: 1240, transform: `scale(${win})`, transformOrigin: "50% 0%", opacity: Math.min(1, win * 1.4) }}>
        <CodeWindow tab="server.py · acortado" fontSize={19}>
          <Code text={SERVER} at={0.3} stagger={0.03}
            hl={[{ a: h1, b: h2, lines: [0, 1] }, { a: h2, b: h2 + 1.5, lines: [9, 10, 11] }, { a: h2 + 1.5, b: 7.9, lines: [12, 13, 15, 16, 17, 18, 20] }]} />
        </CodeWindow>
      </div>
      <Card style={{ position: "absolute", left: 1380, top: 250, width: 440, padding: "26px 30px", transform: `scale(${side})`, transformOrigin: "50% 0%", opacity: Math.min(1, side * 1.4) }}>
        <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.06em", color: C.accent }}>EN EL REPO DE EJEMPLOS</div>
        <div style={{ fontFamily: F.mono, fontSize: 19, color: C.ink, marginTop: 8 }}>agente-externo/server.py</div>
        <div style={{ fontFamily: F.body, fontSize: 22, color: C.ink2, marginTop: 6 }}>FastAPI y un LLM compatible con OpenAI</div>
        {LADO.map((r, i) => (
          <div key={r} style={{ display: "flex", gap: 14, padding: "14px 0", borderTop: `2px solid ${C.line}`, marginTop: i === 0 ? 16 : 0,
            opacity: rows[i], transform: `translateX(${(1 - rows[i]) * 14}px)` }}>
            <div style={{ width: 11, height: 11, borderRadius: 6, background: i === 3 ? C.ink : C.accent, flexShrink: 0, marginTop: 10 }} />
            <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.ink, lineHeight: 1.25 }}>{r}</span>
          </div>
        ))}
      </Card>
    </AbsoluteFill>
  );
};

// ---------- 5. configurarlo ----------

const Campo: React.FC<{ label: string; value: string; p?: number; mono?: boolean; hint?: string }> = ({ label, value, p = 1, mono, hint }) => (
  <div style={{ marginTop: 12 }}>
    <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 23, color: C.ink }}>{label}</div>
    {hint ? <div style={{ fontFamily: F.body, fontSize: 18, color: C.muted }}>{hint}</div> : null}
    <div style={{ marginTop: 5, border: `1.5px solid ${C.line2}`, borderRadius: 8, padding: "8px 14px", fontFamily: mono ? F.mono : F.body, fontSize: 23,
      color: C.ink, minHeight: 22, background: "#fff" }}>
      <span style={{ opacity: p }}>{value}</span>
    </div>
  </div>
);

const Paso: React.FC<{ n: number; title: string; where: string; x: number; p: number; on: boolean; children: React.ReactNode }> = ({ n, title, where, x, p, on, children }) => (
  <Card style={{ position: "absolute", left: x, top: 240, width: 545, height: 530, padding: "22px 26px", borderColor: on ? C.accent : C.line,
    transform: `scale(${p})`, transformOrigin: "50% 0%", opacity: Math.min(1, p * 1.4) }}>
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <div style={{ width: 46, height: 46, borderRadius: 23, background: on ? C.accent : C.ink, color: "#fff", fontFamily: F.display, fontWeight: 800, fontSize: 26,
        display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{n}</div>
      <div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, lineHeight: 1.05 }}>{title}</div>
        <div style={{ fontFamily: F.mono, fontSize: 16, color: C.muted, marginTop: 2 }}>{where}</div>
      </div>
    </div>
    <div style={{ marginTop: 10 }}>{children}</div>
  </Card>
);

const Switch: React.FC<{ on: number }> = ({ on }) => (
  <div style={{ width: 52, height: 28, borderRadius: 14, background: on > 0.5 ? C.accent : C.line2, position: "relative", flexShrink: 0 }}>
    <div style={{ position: "absolute", top: 3, left: 3 + on * 24, width: 22, height: 22, borderRadius: 11, background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,.25)" }} />
  </div>
);

export const Configurar: React.FC = () => {
  const t = useT();
  const s1 = sub("t6", 1), s2 = sub("t6", 2), s3 = sub("t6", 3);
  const p1 = usePop(0.4), p2 = usePop(0.7), p3 = usePop(1.0);
  const tipo = useIn(s1 + 0.2, 0.3);
  const f1 = useIn(s1 + 0.7, 0.3), f2 = useIn(s1 + 1.3, 0.3), f3 = useIn(s1 + 2.0, 0.3);
  const click = interpolate(t, [s2 + 0.1, s2 + 0.25, s2 + 0.4], [1, 0.92, 1], CLAMP);
  const ok = usePop(s2 + 0.8);
  const sw = interpolate(t, [s3 + 1.0, s3 + 1.3], [0, 1], CLAMP);
  const camposAg = useIn(s3 + 1.5, 0.4);
  const paso = t < s2 ? 1 : t < s3 ? 2 : 3;
  const otros = [usePop(9.4), usePop(9.4 + 1.9)];
  const plan = useIn(2.0, 0.5);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Configurarlo" text="Tres pasos," accent="desde el panel." size={62} />
      <div style={{ position: "absolute", right: 120, top: 110 }}><PlanBadge p={plan} style={{ fontSize: 26, padding: "10px 18px" }}>Incluido en el plan Red</PlanBadge></div>
      <Paso n={1} title="La conexión" where="Configuración › Modelos › Nueva conexión" x={120} p={p1} on={paso === 1}>
        <div style={{ border: `2px solid ${C.accent}`, background: C.accentSoft, borderRadius: 10, padding: "8px 14px", display: "flex", alignItems: "center", gap: 10, opacity: tipo }}>
          <div style={{ width: 18, height: 18, borderRadius: 9, border: `5px solid ${C.accent}`, background: "#fff" }} />
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 23, color: C.ink }}>OpenAI compatible</span>
        </div>
        <Campo label="Nombre" value="Mi agente" p={f1} />
        <Campo label="URL base" value="https://tu-agente.com/v1" p={f2} mono />
        <Campo label="API key" value="••••••••••••" p={f3} hint="Se guarda cifrada y no se vuelve a mostrar." />
      </Paso>
      <Paso n={2} title="La prueba" where="En el agente · Probar el endpoint" x={688} p={p2} on={paso === 2}>
        <div style={{ fontFamily: F.body, fontSize: 24, color: C.ink2, lineHeight: 1.35 }}>
          Le manda a tu endpoint un turno como los de una llamada y mide cuánto tarda el primer texto.
        </div>
        <div style={{ display: "inline-block", marginTop: 18, border: `1.5px solid ${C.line2}`, borderRadius: 8, padding: "9px 18px", fontFamily: F.body, fontWeight: 700,
          fontSize: 23, color: C.ink, transform: `scale(${click})`, background: t > s2 + 0.1 && t < s2 + 0.8 ? C.surface2 : "#fff" }}>
          Probar el endpoint
        </div>
        <div style={{ marginTop: 20, borderLeft: `5px solid ${C.ok}`, background: "#fff", boxShadow: shadowCard, borderRadius: 10, padding: "12px 16px",
          transform: `scale(${ok})`, opacity: Math.min(1, ok * 1.4), border: `1.5px solid ${C.line}`, borderLeftWidth: 5, borderLeftColor: C.ok }}>
          <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink }}>Tu agente respondió</div>
          <div style={{ fontFamily: F.mono, fontSize: 19, color: C.ink2, marginTop: 4 }}>streaming · primer texto 420 ms</div>
          <div style={{ fontFamily: F.mono, fontSize: 19, color: C.ink2 }}>«Hola, ...»</div>
        </div>
        <Nota p={ok} style={{ marginTop: 10, fontSize: 17 }}>Ejemplo de la documentación</Nota>
      </Paso>
      <Paso n={3} title="El agente" where="Definición · Tu propio agente" x={1256} p={p3} on={paso === 3}>
        <div style={{ display: "flex", gap: 14, alignItems: "flex-start", marginTop: 4 }}>
          <Switch on={sw} />
          <div>
            <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.ink }}>Que conteste tu propio agente</div>
            <div style={{ fontFamily: F.body, fontSize: 18, color: C.muted, lineHeight: 1.3 }}>
              En cada turno, Atentina le manda la conversación a tu endpoint y dice lo que responde.
            </div>
          </div>
        </div>
        <div style={{ opacity: camposAg }}>
          <Campo label="Endpoint" value="Mi agente" />
          <Campo label="Modelo" value="ventas" mono />
          <div style={{ fontFamily: F.body, fontSize: 18, color: C.muted, marginTop: 12, lineHeight: 1.3 }}>
            Tu agente recibe dos herramientas: end_call y transfer_call. Los datos de la llamada llegan en los headers X-Atentina-*.
          </div>
        </div>
      </Paso>
      <div style={{ position: "absolute", left: 120, top: 800, right: 120, display: "flex", gap: 22 }}>
        {[
          { m: "API", k: "key calls", tools: "POST /clients/{id}/llm-connections · /test · POST /agents" },
          { m: "MCP", k: "tu agente de IA", tools: "create_llm_connection · test_llm_connection · create_agent" },
        ].map((x, i) => (
          <div key={x.m} style={{ flex: 1, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 20, padding: "14px 22px", boxShadow: shadowCard,
            transform: `scale(${otros[i]})`, opacity: Math.min(1, otros[i] * 1.4) }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Por {x.m}</span>
              <Mono size={18}>{x.k}</Mono>
            </div>
            <div style={{ fontFamily: F.mono, fontSize: 20, color: C.accent2, marginTop: 6 }}>{x.tools}</div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ---------- 6. latencia: el tiempo hasta el primer texto (concepto, sin cifras medidas) ----------

const FACTORES = [
  { t: "Tu modelo", s: "Cuánto tarda en empezar a generar" },
  { t: "Tus herramientas", s: "Lo que consultás antes de responder" },
  { t: "Tu infraestructura", s: "Dónde corre y qué tan cargada está" },
];

export const Latencia: React.FC = () => {
  const t = useT();
  const s1 = sub("t8", 1), s2 = sub("t8", 2), s3 = sub("t8", 3), s4 = sub("t8", 4);
  const card = usePop(0.3);
  const n0 = usePop(s1 - 0.2);
  const bar = interpolate(t, [s1 + 0.3, s2 + 0.6], [0, 1], CLAMP);
  const n1 = usePop(s2 + 0.6);
  const voz = usePop(s2 + 1.4);
  const label = useIn(0.8, 0.5);
  const fs = FACTORES.map((_, i) => usePop(s3 + 0.2 + i * 0.7));
  const lenta = usePop(s4);
  const tip = useIn(s4 + 1.6, 0.5);
  const X0 = 250, X1 = 1290, Y = 440; // del pedido al primer pedazo
  return (
    <AbsoluteFill>
      <Headline eyebrow="Latencia" text="El primer texto es" accent="lo que más pesa." size={62} />
      <Card style={{ position: "absolute", left: 120, top: 250, width: 1680, height: 350, transform: `scale(${card})`, transformOrigin: "50% 0%", opacity: Math.min(1, card * 1.4) }}>
        <div style={{ position: "absolute", left: 40, top: 26, opacity: label }}>
          <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Tiempo hasta el primer texto</span>
          <span style={{ fontFamily: F.mono, fontSize: 20, color: C.muted, marginLeft: 16 }}>time to first token</span>
        </div>
      </Card>
      <div style={{ position: "absolute", left: X0, top: Y - 7, width: (X1 - X0) * bar, height: 14, borderRadius: 7, background: C.accent, opacity: card }} />
      <div style={{ position: "absolute", left: X0, top: Y - 7, width: X1 - X0, height: 14, borderRadius: 7, border: `2px dashed ${C.line2}`, opacity: card * 0.8 }} />
      {[
        { x: X0, p: n0, t: "Tu endpoint recibe el pedido", dark: true },
        { x: X1, p: n1, t: "Manda el primer pedazo de texto", dark: true },
      ].map((n) => (
        <div key={n.t} style={{ position: "absolute", left: n.x - 150, top: Y - 40, width: 300, display: "flex", flexDirection: "column", alignItems: "center",
          transform: `scale(${n.p})`, opacity: Math.min(1, n.p * 1.4) }}>
          <div style={{ width: 80, height: 80, borderRadius: 20, background: C.ink, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <IconoCodigo size={46} color="#fff" />
          </div>
          <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.ink, textAlign: "center", marginTop: 10 }}>{n.t}</div>
        </div>
      ))}
      <div style={{ position: "absolute", left: 1500, top: Y - 40, width: 260, display: "flex", flexDirection: "column", alignItems: "center",
        transform: `scale(${voz})`, opacity: Math.min(1, voz * 1.4) }}>
        <AgenteLogo size={80} talk={voz > 0.9 ? 0.7 : 0} />
        <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.accent2, textAlign: "center", marginTop: 10 }}>Atentina lo dice en voz</div>
      </div>
      <div style={{ position: "absolute", left: 1330, top: Y - 4, width: 160, borderTop: `3px dotted ${C.line2}`, opacity: voz }} />
      <div style={{ position: "absolute", left: 120, top: 640, display: "flex", gap: 22 }}>
        {FACTORES.map((x, i) => (
          <div key={x.t} style={{ width: 400, background: "#fff", border: `2px solid ${C.accent}`, borderRadius: 20, padding: "18px 24px", boxShadow: shadowCard,
            transform: `scale(${fs[i]})`, opacity: Math.min(1, fs[i] * 1.4) }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>{x.t}</div>
            <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink2, marginTop: 4 }}>{x.s}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 1420, top: 640, width: 380, background: C.warnSoft, border: `2px solid ${C.warn}`, borderRadius: 20, padding: "18px 24px",
        transform: `scale(${lenta})`, opacity: Math.min(1, lenta * 1.4) }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.warn }}>Más de 1 s</div>
        <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink, marginTop: 4 }}>Se siente lenta, con silencios</div>
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 850, display: "flex", justifyContent: "center", opacity: tip, transform: `translateY(${(1 - tip) * 12}px)` }}>
        <div style={{ background: C.accentSoft, borderRadius: 18, padding: "14px 30px", fontFamily: F.body, fontSize: 27, color: C.ink }}>
          Mandá el texto apenas lo tengas, y las herramientas lentas, después de <b>«Dame un segundo que me fijo»</b>.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 7. errores ----------

export const Errores: React.FC = () => {
  const ep = usePop(0.3);
  const msg = usePop(sub("t9", 0) + 1.6);
  const corta = usePop(sub("t9", 1) + 0.3);
  const deriva = usePop(sub("t9", 2) + 0.6);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Errores" text="Si tu endpoint falla," accent="el agente avisa." size={62} />
      <Card style={{ position: "absolute", left: 120, top: 320, width: 470, height: 290, padding: "28px 32px", borderColor: C.warn,
        transform: `scale(${ep})`, opacity: Math.min(1, ep * 1.4) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ width: 76, height: 76, borderRadius: 20, background: C.ink, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
            <IconoCodigo size={44} color="#fff" />
            <div style={{ position: "absolute", right: -12, top: -12, width: 34, height: 34, borderRadius: 17, background: C.warn, color: "#fff", fontFamily: F.display,
              fontWeight: 800, fontSize: 22, display: "flex", alignItems: "center", justifyContent: "center" }}>×</div>
          </div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Tu endpoint</div>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 26, color: C.ink2, marginTop: 20, lineHeight: 1.35 }}>
          Da error, responde vacío o no manda texto en <span style={{ fontFamily: F.mono, fontSize: 20 }}>first_token_timeout_ms</span>
        </div>
      </Card>
      <div style={{ position: "absolute", left: 640, top: 330, display: "flex", alignItems: "center", gap: 18, transform: `scale(${msg})`, opacity: Math.min(1, msg * 1.4) }}>
        <AgenteLogo size={96} talk={msg > 0.9 ? 0.6 : 0} />
        <div style={{ background: "#fff", border: `2px solid ${C.line}`, borderRadius: 22, padding: "18px 24px", boxShadow: shadowCard }}>
          <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 30, color: C.ink }}>«Disculpá, se me cortó. ¿Me lo repetís?»</div>
          <div style={{ fontFamily: F.mono, fontSize: 18, color: C.muted, marginTop: 6 }}>error_message · el mensaje que configuraste</div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 640, top: 530, fontFamily: F.body, fontSize: 28, color: C.ink2, opacity: corta }}>
        Con <span style={{ fontFamily: F.mono, fontSize: 22 }}>max_errors</span> seguidos (2 por defecto):
      </div>
      <div style={{ position: "absolute", left: 640, top: 585, display: "flex", gap: 22 }}>
        {[
          { p: corta, t: "Corta", m: "hang_up · external_error" },
          { p: deriva, t: "Pasa a tu equipo", m: "transfer:<área>" },
        ].map((x) => (
          <div key={x.t} style={{ width: 560, background: "#fff", border: `2px solid ${C.accent}`, borderRadius: 20, padding: "22px 28px", boxShadow: shadowCard,
            transform: `scale(${x.p})`, opacity: Math.min(1, x.p * 1.4) }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink }}>{x.t}</div>
            <div style={{ fontFamily: F.mono, fontSize: 22, color: C.accent2, marginTop: 4 }}>{x.m}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 640, top: 760, fontFamily: F.body, fontSize: 24, color: C.muted, opacity: deriva }}>
        Un turno bueno vuelve el contador a cero.
      </div>
    </AbsoluteFill>
  );
};

// ---------- 8. cierre ----------

export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const title = useIn(0.4, 0.7);
  const PASOS = ["La conexión", "Probar el endpoint", "Que conteste tu propio agente"];
  const ps = PASOS.map((_, i) => usePop(1.6 + i * 0.35));
  const plan = useIn(sub("t10", 1), 0.5);
  const url = useIn(sub("t10", 2) - 0.2, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 100, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 340 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 230, textAlign: "center", fontFamily: F.mono, fontSize: 24, letterSpacing: "0.1em", color: C.accentOnDark, opacity: title }}>
        TU PROPIO AGENTE · CUSTOM LLM
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 280, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 76, lineHeight: 1.08,
        color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em" }}>
        Tu agente, con nuestra voz<br /><span style={{ color: C.accentOnDark }}>y nuestro teléfono.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 500, display: "flex", justifyContent: "center", gap: 20 }}>
        {PASOS.map((p, i) => (
          <div key={p} style={{ display: "flex", alignItems: "center", gap: 14, background: "#16213a", border: "2px solid #23304d", borderRadius: 999, padding: "12px 26px",
            transform: `scale(${ps[i]})`, opacity: Math.min(1, ps[i] * 1.4) }}>
            <span style={{ width: 36, height: 36, borderRadius: 18, background: "#1d2f63", color: C.accentOnDark, fontFamily: F.display, fontWeight: 800, fontSize: 22,
              display: "inline-flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</span>
            <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 28, color: C.ctaInk }}>{p}</span>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 610, display: "flex", justifyContent: "center" }}>
        <PlanBadge p={plan} dark style={{ fontSize: 26, padding: "10px 18px" }}>Incluido en el plan Red</PlanBadge>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 710, display: "flex", justifyContent: "center", opacity: url, transform: `translateY(${(1 - url) * 16}px)` }}>
        <div style={{ background: "#fff", color: C.ink, borderRadius: 999, padding: "16px 36px", fontFamily: F.mono, fontSize: 34 }}>
          atentina.com.ar<span style={{ color: C.accent }}>/desarrolladores/docs/tu-propio-agente</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

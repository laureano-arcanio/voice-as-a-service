import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile } from "remotion";
import { AgenteLogo, CAST, Person } from "../../../src/comun/characters";
import { CodeLine, CodeWindow } from "../../../src/comun/code";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { Card, Headline, Icon, useIn, usePop, Wave } from "../../../src/comun/ui";
import { IconoCodigo, Mono, Nota, useT } from "./piezas";
import { sub } from "./timeline";

// ---------- 0. intro ----------

const CANALES = [
  { i: "phone" as const, t: "Llamadas" },
  { i: "wa" as const, t: "WhatsApp" },
  { i: "web" as const, t: "Link para llamar" },
];

export const Intro: React.FC = () => {
  const t = useT();
  const logo = usePop(0.15);
  const title = useIn(0.4, 0.7);
  const a0 = sub("t1", 1);
  const ats = [a0, a0 + 0.55, a0 + 1.1];
  const chips = ats.map((a) => usePop(a));
  const num = usePop(a0 + 2.0);
  const ep = useIn(1.6, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 380 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 270, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.2, 0.5) }}>
        TU PROPIO AGENTE · CUSTOM LLM
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 330, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 96,
        lineHeight: 1.06, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Tu agente, <span style={{ color: C.accentOnDark }}>nuestra voz.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 470, display: "flex", justifyContent: "center", opacity: ep, transform: `translateY(${(1 - ep) * 12}px)` }}>
        <div style={{ fontFamily: F.mono, fontSize: 28, color: C.ctaMuted, background: "#111a2e", border: "2px solid #23304d", borderRadius: 14, padding: "10px 22px" }}>
          tu endpoint · <span style={{ color: C.ctaInk }}>POST /chat/completions</span> · <span style={{ color: "#5ee49a" }}>stream: true</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 640, display: "flex", justifyContent: "center", gap: 24 }}>
        {CANALES.map((x, i) => {
          const on = interpolate(t, [ats[i], ats[i] + 0.2, ats[i] + 1.0, ats[i] + 1.2], [0, 1, 1, 0], CLAMP);
          return (
            <div key={x.t} style={{
              display: "inline-flex", alignItems: "center", gap: 14, borderRadius: 999, padding: "14px 28px", fontFamily: F.body, fontWeight: 700, fontSize: 32,
              background: on > 0.5 ? "#1d2f63" : "#16213a", color: C.ctaInk, border: `2px solid ${on > 0.5 ? C.accentOnDark : "#23304d"}`,
              transform: `scale(${chips[i]})`, opacity: Math.min(1, chips[i] * 1.5), whiteSpace: "nowrap",
            }}>
              <Icon name={x.i} size={34} color={C.accentOnDark} />
              {x.t}
            </div>
          );
        })}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 12, borderRadius: 999, padding: "14px 28px", fontFamily: F.body, fontWeight: 700, fontSize: 32,
          background: C.accent, color: "#fff", transform: `scale(${num})`, opacity: Math.min(1, num * 1.5), whiteSpace: "nowrap",
        }}>
          Número argentino
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 770, textAlign: "center", fontFamily: F.body, fontSize: 30, color: C.ctaMuted, opacity: useIn(sub("t1", 2), 0.5) }}>
        Sin armar el pipeline de voz
      </div>
    </AbsoluteFill>
  );
};

// ---------- 1. qué pone cada uno ----------

const ATENTINA = [
  "El número, las llamadas entrantes y salientes",
  "WhatsApp y el link para llamar",
  "La transcripción, los turnos y las interrupciones",
  "La voz argentina y la grabación",
  "Los minutos, la derivación y el registro en el panel",
];
const TUYO = [
  "El prompt y la personalidad",
  "Las herramientas y tus sistemas",
  "La memoria y el estado",
  "Qué responder en cada turno",
];

const Lista: React.FC<{ rows: string[]; a: number; b: number; color: string }> = ({ rows, a, b, color }) => {
  const ps = rows.map((_, i) => useIn(a + ((b - a) * i) / rows.length, 0.4));
  return (
    <>
      {rows.map((r, i) => (
        <div key={r} style={{ display: "flex", alignItems: "center", gap: 16, padding: "17px 0", borderTop: `2px solid ${C.line}`,
          opacity: ps[i], transform: `translateX(${(1 - ps[i]) * 16}px)` }}>
          <div style={{ width: 12, height: 12, borderRadius: 6, background: color, flexShrink: 0 }} />
          <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 29, color: C.ink }}>{r}</span>
        </div>
      ))}
    </>
  );
};

export const Reparto: React.FC = () => {
  const l = usePop(0.3);
  const r = usePop(sub("t2", 2) - 0.2);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Qué es" text="Atentina pone la voz," accent="tu agente, las respuestas." size={62} />
      <Card style={{ position: "absolute", left: 120, top: 280, width: 860, height: 600, padding: "28px 36px", borderColor: C.accent,
        transform: `scale(${l})`, transformOrigin: "50% 0%", opacity: Math.min(1, l * 1.4) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 16 }}>
          <AgenteLogo size={78} />
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent }}>PONE ATENTINA</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ink }}>La voz y el canal</div>
          </div>
        </div>
        <Lista rows={ATENTINA} a={0.6} b={sub("t2", 2) - 0.3} color={C.accent} />
      </Card>
      <Card style={{ position: "absolute", left: 1020, top: 280, width: 780, height: 600, padding: "28px 36px",
        transform: `scale(${r})`, transformOrigin: "50% 0%", opacity: Math.min(1, r * 1.4) }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 16 }}>
          <div style={{ width: 78, height: 78, borderRadius: 39, background: C.ink, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <IconoCodigo size={44} color="#fff" />
          </div>
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.ink2 }}>PONE TU AGENTE</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ink }}>Qué responder</div>
          </div>
        </div>
        <Lista rows={TUYO} a={sub("t2", 2)} b={sub("t2", 3) + 1.6} color={C.ink} />
      </Card>
    </AbsoluteFill>
  );
};

// ---------- 2. un turno ----------

const PEDIDO = `X-Atentina-Conversation-Id: 6f1c2a9e-...
X-Atentina-Channel: voice
X-Atentina-From: +5493515551234
X-Atentina-Turn: 2
{"model": "ventas", "stream": true,
 "messages": [
   {"role": "assistant", "content": "Hola, soy Sofía de Acme..."},
   ...
   {"role": "user", "content": "A las cuatro. Nada más, gracias."}
 ],
 "tools": [{... "name": "end_call" ...}]}`;

const CHUNKS = ["Perfecto, te espero el jueves ", "a las cuatro."];

/** Paquete que viaja entre dos puntos (onda = voz, Aa = texto). */
const Paquete: React.FC<{ a: number; b: number; x0: number; x1: number; y: number; kind: "aa" | "voz" }> = ({ a, b, x0, x1, y, kind }) => {
  const t = useT();
  const p = interpolate(t, [a, b], [0, 1], { ...CLAMP, easing: EASE });
  if (t < a || t > b + 0.05) return null;
  const x = x0 + (x1 - x0) * p;
  return (
    <div style={{ position: "absolute", left: x - 36, top: y - 24, width: 72, height: 48, borderRadius: 14, background: C.accent, color: "#fff",
      fontFamily: F.display, fontWeight: 800, fontSize: 24, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 10px 24px rgba(36,86,230,.3)" }}>
      {kind === "aa" ? "Aa" : <Wave n={5} h={24} />}
    </div>
  );
};

export const Turno: React.FC = () => {
  const t = useT();
  const person = usePop(0.2);
  const at = usePop(0.4);
  const ep = usePop(0.6);
  const ida = sub("t3", 0) + 1.6; // la conversación viaja a tu endpoint
  const vuelta = sub("t3", 2);     // contesta en streaming
  const voz = sub("t3", 3);
  const req = usePop(sub("t3", 1) - 0.3);
  const res = usePop(vuelta - 0.2);
  const ch = [useIn(vuelta + 0.3, 0.3), useIn(vuelta + 1.3, 0.3)];
  const dice = [useIn(voz + 0.1, 0.3), useIn(voz + 1.1, 0.3)];
  const activo = t > ida - 0.3 && t < vuelta + 0.4 ? "ep" : t >= vuelta + 0.4 ? "at" : "";
  const y = 345;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Cómo funciona" text="En cada turno, tu endpoint" accent="decide qué decir." size={62} />
      {/* conexiones */}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <line x1={430} y1={y} x2={640} y2={y} stroke={C.line2} strokeWidth={4} strokeDasharray="10 10" />
        <line x1={1190} y1={y} x2={1380} y2={y} stroke={C.line2} strokeWidth={4} strokeDasharray="10 10" />
      </svg>
      <div style={{ position: "absolute", left: 150, top: 225, width: 280, height: 260, overflow: "hidden", transform: `scale(${person})`, opacity: Math.min(1, person * 1.4) }}>
        <Person {...CAST.cliente} size={250} pose="phone" mood="happy" style={{ marginLeft: 10 }} />
      </div>
      <Card style={{ position: "absolute", left: 640, top: 260, width: 550, height: 170, padding: "0 28px", display: "flex", alignItems: "center", gap: 22,
        borderColor: activo === "at" ? C.accent : C.line, transform: `scale(${at * (activo === "at" ? 1.04 : 1)})`, opacity: Math.min(1, at * 1.4) }}>
        <AgenteLogo size={100} talk={t > voz && t < voz + 2.6 ? 0.8 : 0} />
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink }}>Atentina</div>
          <div style={{ fontFamily: F.body, fontSize: 23, color: C.ink2 }}>
            {t < voz ? "Transcribe y detecta el fin del turno" : "Lo dice en voz apenas llega"}
          </div>
        </div>
      </Card>
      <Card style={{ position: "absolute", left: 1380, top: 260, width: 420, height: 170, padding: "0 26px", display: "flex", alignItems: "center", gap: 20,
        borderColor: activo === "ep" ? C.accent : C.line, transform: `scale(${ep * (activo === "ep" ? 1.04 : 1)})`, opacity: Math.min(1, ep * 1.4) }}>
        <div style={{ width: 88, height: 88, borderRadius: 22, background: C.ink, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <IconoCodigo size={50} color="#fff" />
        </div>
        <div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Tu endpoint</div>
          <div style={{ fontFamily: F.mono, fontSize: 19, color: C.accent2 }}>tu-agente.com/v1</div>
        </div>
      </Card>
      {/* la persona habla -> Atentina; la conversación -> tu endpoint; el texto vuelve; la voz sale */}
      <Paquete a={0.5} b={1.5} x0={430} x1={640} y={y} kind="voz" />
      <Paquete a={ida} b={ida + 1.0} x0={1190} x1={1380} y={y} kind="aa" />
      <Paquete a={vuelta + 0.2} b={vuelta + 1.0} x0={1380} x1={1190} y={y} kind="aa" />
      <Paquete a={vuelta + 1.2} b={vuelta + 2.0} x0={1380} x1={1190} y={y} kind="aa" />
      <Paquete a={voz + 0.1} b={voz + 1.1} x0={640} x1={430} y={y} kind="voz" />
      <Paquete a={voz + 1.1} b={voz + 2.1} x0={640} x1={430} y={y} kind="voz" />
      {/* lo que dice, por pedazos */}
      <div style={{ position: "absolute", left: 640, top: 444, width: 560, fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.accent2 }}>
        <span style={{ opacity: dice[0] }}>«{CHUNKS[0]}</span><span style={{ opacity: dice[1] }}>{CHUNKS[1]}»</span>
      </div>
      <div style={{ position: "absolute", left: 120, top: 485, width: 1010, transform: `scale(${req})`, transformOrigin: "50% 0%", opacity: Math.min(1, req * 1.4) }}>
        <CodeWindow tab="pedido de Atentina" method="POST" path="https://tu-agente.com/v1/chat/completions" fontSize={18}>
          {PEDIDO.split("\n").map((l, i) => <CodeLine key={i} line={l} />)}
        </CodeWindow>
      </div>
      <div style={{ position: "absolute", left: 1170, top: 485, width: 630, transform: `scale(${res})`, transformOrigin: "50% 0%", opacity: Math.min(1, res * 1.4) }}>
        <CodeWindow tab="respuesta · SSE" fontSize={19} minHeight={250}>
          {CHUNKS.map((c, i) => (
            <div key={c} style={{ opacity: ch[i], marginBottom: 10 }}>
              <CodeLine line={`data: {"choices":[{"delta":`} />
              <CodeLine line={`  {"content":"${c}"}}]}`} />
            </div>
          ))}
          <div style={{ opacity: useIn(vuelta + 2.2, 0.3) }}><CodeLine line="data: [DONE]" /></div>
        </CodeWindow>
        <Nota p={res} style={{ marginTop: 10 }}>Ejemplo de la documentación, recortado</Nota>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 3. herramientas ----------

const TOOL_SSE = `data: {"choices":[{"delta":{"tool_calls":[{"type":"function",
       "function":{"name":"end_call","arguments":"{\\"outcome\\": \\"turno_dado\\"}"}}]}}]}`;

export const Herramientas: React.FC = () => {
  const a = usePop(sub("t4", 2) - 0.2);
  const b = usePop(sub("t4", 2) + 1.9);
  const sse = usePop(1.0);
  const res = usePop(sub("t4", 2) + 0.9);
  const TOOLS = [
    { p: a, eb: "CORTAR", n: "end_call", rows: ["Corta cuando termina la despedida", "Con outcome elige el resultado, entre los del agente"] },
    { p: b, eb: "DERIVAR", n: "transfer_call", rows: ["Pasa la llamada a un área de tu equipo", "La persona escucha música; si nadie atiende, el agente retoma"] },
  ];
  return (
    <AbsoluteFill>
      <Headline eyebrow="Herramientas" text="Tu agente corta o deriva," accent="con dos herramientas." size={62} />
      {TOOLS.map((x, i) => (
        <Card key={x.n} style={{ position: "absolute", left: 120 + i * 850, top: 270, width: 830, height: 370, padding: "30px 38px",
          borderColor: C.accent, transform: `scale(${x.p})`, transformOrigin: "50% 0%", opacity: Math.min(1, x.p * 1.4) }}>
          <div style={{ fontFamily: F.mono, fontSize: 20, letterSpacing: "0.08em", color: C.accent }}>{x.eb}</div>
          <div style={{ fontFamily: F.mono, fontSize: 44, color: C.ink, margin: "6px 0 10px" }}>{x.n}</div>
          {x.rows.map((r) => (
            <div key={r} style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 0", borderTop: `2px solid ${C.line}` }}>
              <div style={{ width: 12, height: 12, borderRadius: 6, background: C.accent, flexShrink: 0 }} />
              <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 30, color: C.ink }}>{r}</span>
            </div>
          ))}
          {i === 1 ? <Nota style={{ marginTop: 6 }}>Llega si el agente tiene áreas de derivación</Nota> : null}
        </Card>
      ))}
      <div style={{ position: "absolute", left: 120, top: 690, width: 1180, transform: `scale(${sse})`, transformOrigin: "50% 0%", opacity: Math.min(1, sse * 1.4) }}>
        <CodeWindow tab="respuesta · SSE" fontSize={21}>
          {TOOL_SSE.split("\n").map((l, i) => <CodeLine key={i} line={l} />)}
        </CodeWindow>
        <Nota p={sse} style={{ marginTop: 10 }}>Las manda Atentina en tools y las ejecuta Atentina · ejemplo de la documentación</Nota>
      </div>
      <Card style={{ position: "absolute", left: 1340, top: 700, width: 460, padding: "22px 28px", transform: `scale(${res})`, opacity: Math.min(1, res * 1.4) }}>
        <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>LA LLAMADA TERMINA</div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 10 }}>
          <span style={{ fontFamily: F.body, fontWeight: 700, fontSize: 26, color: C.ink }}>Resultado</span>
          <Mono size={22} style={{ background: C.okSoft, color: C.ok }}>turno_dado</Mono>
        </div>
      </Card>
    </AbsoluteFill>
  );
};

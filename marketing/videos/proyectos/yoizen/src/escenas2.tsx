import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { CodeWindow, Ok, Typed } from "../../../src/comun/code";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, Icon, Pill, useIn, usePop, Wave } from "../../../src/comun/ui";

const CALL_JSON = `{
  "agent_id": "8f3c…",
  "phone": "+54 11 5555 0101",
  "context": "Consultó por su factura de octubre"
}`;

const RESULT_JSON = `{
  "outcome": { "label": "Consulta resuelta", "goal": true },
  "fields": [
    { "name": "motivo", "value": "Factura de octubre" }
  ],
  "messages": [ … ],
  "call": { "duration_seconds": 74 }
}`;

const ChatMsg: React.FC<{ me?: boolean; p: number; children: React.ReactNode }> = ({ me, p, children }) => (
  <div style={{
    alignSelf: me ? "flex-start" : "flex-end", maxWidth: 330, opacity: p, transform: `translateY(${(1 - p) * 12}px)`,
    background: me ? C.surface2 : C.ink2, color: me ? C.ink : "#fff", borderRadius: 16, padding: "10px 16px", fontFamily: F.body, fontSize: 21, lineHeight: 1.3,
  }}>
    {children}
  </div>
);

/** 3. API de llamadas: del chat a una llamada con contexto, y el resultado de vuelta al ticket. */
export const Llamadas: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const chat = usePop(0.3);
  const msgs = [useIn(0.7, 0.3), useIn(1.3, 0.3)];
  const post = usePop(1.5);
  const call = usePop(3.9);
  const ringing = t > 3.9 && t < 4.7;
  const talking = t >= 4.7 && t < 7.2;
  const bubble = useIn(4.7, 0.3);
  const get = usePop(7.0);
  const ticket = usePop(8.9);
  const back = interpolate(t, [8.6, 9.0], [0, 1], CLAMP);
  const also = usePop(9.6);
  const shake = ringing ? Math.sin(frame * 1.8) * 4 : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="API de llamadas" text="Entrantes y salientes," accent="con el contexto del chat." />

      {/* Web chat de Yoizen */}
      <Card style={{ position: "absolute", left: 90, top: 290, width: 440, padding: "18px 22px", transform: `scale(${chat})`, transformOrigin: "50% 0%", background: "#fbfcfe", borderColor: C.line2 }}>
        <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: C.muted }}>WEB CHAT · YOIZEN</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
          <ChatMsg me p={msgs[0]}>Quiero que me llamen por mi factura de octubre.</ChatMsg>
          <ChatMsg p={msgs[1]}>¡Listo! Te llamamos en un momento.</ChatMsg>
        </div>
      </Card>

      {/* El pedido de llamada */}
      <div style={{ position: "absolute", left: 575, top: 290, width: 690, transform: `scale(${post})`, transformOrigin: "50% 0%" }}>
        <CodeWindow tab="llamar.json" method="POST" path="/api/v1/calls" status={t > 3.7 ? <Ok>201 Created</Ok> : null} fontSize={19} minHeight={170}>
          <Typed text={CALL_JSON} a={1.7} b={3.6} t={t} />
        </CodeWindow>
      </div>

      {/* La llamada */}
      <div style={{ position: "absolute", left: 1320, top: 300, width: 510, height: 330, borderRadius: 32, background: C.accentSoft, transform: `scale(${call})` }} />
      <div style={{ position: "absolute", left: 1330, top: 330, transform: `scale(${call}) rotate(${shake}deg)`, transformOrigin: "50% 100%" }}>
        <Person {...CAST.cliente} size={300} pose="phone" mood={talking || t > 7.2 ? "happy" : "neutral"} />
      </div>
      <div style={{ position: "absolute", left: 1590, top: 330, transform: `scale(${call})`, transformOrigin: "50% 100%" }}>
        <Mascot size={300} talk={talking ? 0.3 + 0.4 * Math.abs(Math.sin(frame / 3.2)) : 0} />
      </div>
      {talking ? (
        <div style={{ position: "absolute", left: 1555, top: 315, background: C.accent, borderRadius: 999, padding: "6px 14px" }}><Wave n={5} h={20} /></div>
      ) : null}
      <div style={{
        position: "absolute", left: 1320, top: 645, width: 510, opacity: bubble, background: "#fff", border: `2px solid ${C.line}`, borderRadius: 20,
        padding: "12px 18px", fontFamily: F.body, fontSize: 21, lineHeight: 1.35, color: C.ink, boxShadow: shadowCard,
      }}>
        <span style={{ fontFamily: F.mono, fontSize: 16, color: C.accent }}>ATENTINA · </span>
        “Hola, Carolina. Te llamo por tu consulta de la factura de octubre.”
      </div>

      {/* El resultado */}
      <div style={{ position: "absolute", left: 575, top: 650, width: 690, transform: `scale(${get})`, transformOrigin: "50% 0%" }}>
        <CodeWindow tab="resultado.json" method="GET" path="/api/v1/calls/{id}" status={t > 8.6 ? <Ok>200 OK</Ok> : null} fontSize={17} minHeight={170}>
          <Typed text={RESULT_JSON} a={7.2} b={8.6} t={t} />
        </CodeWindow>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <path d="M570 820 L535 820" stroke={C.ok} strokeWidth={5} strokeDasharray="2 10" strokeLinecap="round" opacity={back} />
      </svg>

      {/* El ticket en su plataforma */}
      <Card style={{ position: "absolute", left: 90, top: 690, width: 440, padding: "18px 22px", transform: `scale(${ticket})`, transformOrigin: "50% 0%", background: "#fbfcfe", borderColor: C.line2 }}>
        <div style={{ fontFamily: F.mono, fontSize: 17, letterSpacing: "0.08em", color: C.muted }}>TICKET #4821 · YOIZEN</div>
        {[["Resultado", "Consulta resuelta"], ["Motivo", "Factura de octubre"], ["Transcripción", "adjunta"]].map(([k, v]) => (
          <div key={k} style={{ display: "grid", gridTemplateColumns: "160px 1fr", padding: "9px 0", borderTop: `1px solid ${C.line}`, fontFamily: F.body, fontSize: 21, marginTop: 4 }}>
            <span style={{ color: C.muted }}>{k}</span><span style={{ fontWeight: 600, color: C.ink }}>{v}</span>
          </div>
        ))}
        <Pill bg={C.okSoft} fg={C.ok} style={{ fontSize: 18, padding: "5px 14px", marginTop: 8 }}><Icon name="check" size={20} /> Actualizado por API</Pill>
      </Card>

      {/* Las otras entradas */}
      <div style={{ position: "absolute", left: 1320, top: 790, width: 520, display: "flex", flexWrap: "wrap", gap: 10, transform: `scale(${also})`, transformOrigin: "0% 0%" }}>
        <div style={{ width: "100%", fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.muted }}>ENTRANTES Y EN LOTE</div>
        {[
          ["phone", "Número propio", C.accent],
          ["wa", "Llamadas de WhatsApp", C.wa],
          ["web", "Link para llamar (web)", C.accent],
          ["calendar", "Campañas + webhook firmado", C.accent],
        ].map(([i, l, c]) => (
          <Pill key={l} bg="#fff" fg={C.ink} style={{ fontSize: 19, padding: "7px 14px", border: `2px solid ${C.line}` }}>
            <Icon name={i as "phone"} size={20} color={c} /> {l}
          </Pill>
        ))}
        <Pill bg="#fff4e5" fg="#b25e09" style={{ fontSize: 19, padding: "7px 14px" }}>
          <Icon name="phone" size={20} /> SIP desde su Asterisk · en evaluación
        </Pill>
      </div>
    </AbsoluteFill>
  );
};

const PY = `from openai import OpenAI

atentina = OpenAI(base_url="https://app.atentina.com.ar/api/v1/inference",
                  api_key="vaas_…")  # una key con alcance stt + tts

texto = atentina.audio.transcriptions.create(model="stt", file=nota, language="es").text
respuesta = bot.responder(texto)  # su bot de texto, sin cambios
audio = atentina.audio.speech.create(model="tts", voice="valentina", input=respuesta)`;

const STEPS = [
  { x: 230, icon: "wa" as const, title: "Nota de voz", sub: "WhatsApp · web chat", ours: false },
  { x: 595, icon: "ear" as const, title: "Transcribe", sub: "/audio/transcriptions", ours: true, metric: "≈ 70 ms en el servidor" },
  { x: 960, icon: "users" as const, title: "Su bot", sub: "Yoizen, sin cambios", ours: false },
  { x: 1325, icon: "speaker" as const, title: "Sintetiza", sub: "/audio/speech", ours: true, metric: "1.er audio ≈ 50 ms (stream)" },
  { x: 1690, icon: "speaker" as const, title: "Respuesta", sub: "en audio, misma voz", ours: false },
];
const SW = 310;
const ROW_Y = 400;

/** 4. API de inferencia: transcripción y síntesis alrededor del bot de texto que ya tienen. */
export const Inferencia: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pops = STEPS.map((_, i) => usePop(0.4 + i * 0.25));
  const code = usePop(2.9);
  const compat = usePop(7.0);
  // Un mensaje recorre el pipeline cada 4 s
  const cyc = t < 1.8 ? -1 : (t - 1.8) % 4;
  const seg = Math.floor(cyc / 0.7);
  const k = interpolate(cyc % 0.7, [0, 0.6], [0, 1], { ...CLAMP, easing: EASE });
  const show = cyc >= 0 && seg < 4;
  const px = show ? STEPS[seg].x + (STEPS[seg + 1].x - STEPS[seg].x) * k : 0;
  const isText = seg === 1 || seg === 2;
  const active = (i: number) => show && ((seg === i - 1 && k > 0.8) || (seg === i && k < 0.3));
  return (
    <AbsoluteFill>
      <Headline eyebrow="API de inferencia" text="Voz para sus bots de texto," accent="sin cambiarlos." />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d={`M${STEPS[0].x} ${ROW_Y} H${STEPS[4].x}`} stroke={C.line2} strokeWidth={5} strokeDasharray="2 14" strokeLinecap="round" opacity={useIn(0.4, 0.5)} />
      </svg>
      {STEPS.map((s, i) => {
        const on = active(i);
        return (
          <React.Fragment key={s.title}>
            <Card style={{
              position: "absolute", left: s.x - SW / 2, top: ROW_Y - 85, width: SW, height: 170, padding: "18px 20px", transform: `scale(${pops[i] * (on ? 1.05 : 1)})`,
              borderColor: on ? C.accent : s.ours ? C.accent : C.line2, background: s.ours ? "#fff" : "#fbfcfe",
              boxShadow: on ? "0 18px 44px rgba(36,86,230,.25)" : shadowCard,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 52, height: 52, borderRadius: 14, background: s.ours ? C.accentSoft : C.surface2, display: "grid", placeItems: "center" }}>
                  <Icon name={s.icon} size={30} color={s.ours ? C.accent : C.ink2} />
                </div>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 31, color: C.ink }}>{s.title}</div>
              </div>
              <div style={{ fontFamily: s.ours ? F.mono : F.body, fontSize: s.ours ? 18 : 20, color: s.ours ? C.accent : C.muted, marginTop: 12, whiteSpace: "nowrap" }}>
                {s.ours ? `POST ${s.sub}` : s.sub}
              </div>
            </Card>
            {s.metric ? (
              <div style={{ position: "absolute", left: s.x - SW / 2, width: SW, top: ROW_Y + 98, textAlign: "center", fontFamily: F.mono, fontSize: 18, color: C.ok, opacity: pops[i] }}>
                {s.metric}
              </div>
            ) : null}
          </React.Fragment>
        );
      })}
      {show ? (
        <div style={{
          position: "absolute", left: px, top: ROW_Y - 118, transform: "translate(-50%, -50%)", background: isText ? C.ink : C.accent, color: "#fff",
          borderRadius: 999, padding: "10px 18px", fontFamily: F.mono, fontSize: 22, boxShadow: "0 10px 26px rgba(36,86,230,.3)",
        }}>
          {isText ? "Aa" : <Wave n={5} h={24} />}
        </div>
      ) : null}

      <div style={{ position: "absolute", left: 160, top: 560, width: 1600, transform: `scale(${code})`, transformOrigin: "50% 0%" }}>
        <CodeWindow tab="bot_con_voz.py" fontSize={21} minHeight={300}>
          <Typed text={PY} a={3.1} b={7.6} t={t} base={C.ctaInk} />
        </CodeWindow>
        <Pill bg={C.okSoft} fg={C.ok} style={{ position: "absolute", right: 24, top: 70, fontSize: 21, transform: `scale(${compat})` }}>
          <Icon name="check" size={22} /> Compatible con el SDK de OpenAI
        </Pill>
      </div>
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import barras from "../../../public/proyectos/api-desarrolladores/vo/demo-barras.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { CodeWindow, Ok } from "../../../src/comun/code";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { Card, Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { AGENT, CALL_OUT, CALL_PHONE, CALL_TEST, CURL_TTS, LLM_OUT, PY_LLM } from "./datos";
import { Code, Nota, PlanBadge, Prompt, Terminal, useT } from "./piezas";
import { AT } from "./timeline";

const Pop: React.FC<{ at: number; style: React.CSSProperties; origin?: string; children: React.ReactNode }> = ({ at, style, origin = "50% 0%", children }) => {
  const p = usePop(at);
  return <div style={{ position: "absolute", transform: `scale(${p})`, transformOrigin: origin, opacity: Math.min(1, p * 1.4), ...style }}>{children}</div>;
};

/** 3. LLM con el SDK de OpenAI: solo cambian base_url y api_key. */
export const Llm: React.FC = () => {
  const out1 = useIn(6.2, 0.3);
  const out2 = useIn(6.8, 0.3);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Demo 1 · LLM" text="El SDK de OpenAI," accent="con otra base_url." />
      <Pop at={0.2} style={{ left: 100, top: 260, width: 1060 }}>
        <CodeWindow tab="llm.py" fontSize={20}>
          <Code text={PY_LLM} at={0.4} hl={[{ a: 1.6, b: 4.3, lines: [4, 5] }, { a: 4.4, b: 6.0, lines: [10] }]} />
        </CodeWindow>
      </Pop>
      <Pop at={5.4} style={{ left: 1200, top: 300, width: 620 }}>
        <Terminal title="python llm.py">
          <Prompt>python llm.py</Prompt>
          <div style={{ opacity: out1, whiteSpace: "normal", color: "#fff", fontSize: 24, margin: "8px 0" }}>{LLM_OUT[0]}</div>
          <div style={{ opacity: out2, color: "#5ee49a" }}>{LLM_OUT[1]}<span style={{ color: "#7d8aa5" }}>   # usage: entrada, salida</span></div>
        </Terminal>
      </Pop>
      <Nota p={useIn(7.2)} style={{ position: "absolute", left: 1200, top: 560, width: 620 }}>
        Salida real del pedido a la URL pública, 25-oct-2026.
      </Nota>
      <Nota p={useIn(7.4)} style={{ position: "absolute", left: 1200, top: 590, width: 620 }}>
        Se descuentan los tokens de usage.
      </Nota>
      <div style={{ position: "absolute", left: 1200, top: 650, opacity: useIn(7.8) }}>
        <PlanBadge>Todos los planes · tokens por mes</PlanBadge>
      </div>
    </AbsoluteFill>
  );
};

/** 4. TTS: el texto a voz, y se escucha el audio real que devolvió. */
export const Tts: React.FC = () => {
  const t = useT();
  const res = useIn(3.2, 0.4);
  const play = interpolate(t, [AT.demo, AT.demo + barras.segundos], [0, 1], CLAMP);
  const playing = t > AT.demo && t < AT.demo + barras.segundos;
  const idx = Math.min(barras.barras.length - 1, Math.floor(play * barras.barras.length));
  const talk = playing ? barras.barras[idx] : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Demo 2 · Síntesis" text="Texto a voz," accent="con acento argentino." />
      <Pop at={0.2} style={{ left: 100, top: 260, width: 1040 }}>
        <CodeWindow tab="terminal" fontSize={20}>
          <Code text={CURL_TTS} at={0.4} hl={[{ a: 1.4, b: 4.4, lines: [3, 4] }]} />
          <div style={{ opacity: res, marginTop: 10, color: "#5ee49a" }}>HTTP 200 · audio/wav · 3,04 s de audio</div>
        </CodeWindow>
      </Pop>
      <Pop at={2.2} style={{ left: 1190, top: 270, width: 630 }}>
        <Card style={{ padding: "22px 26px", borderColor: playing ? C.accent : C.line }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <AgenteLogo size={78} talk={talk} />
            <div>
              <div style={{ fontFamily: F.mono, fontSize: 22, color: C.ink }}>respuesta.wav</div>
              <div style={{ fontFamily: F.body, fontSize: 22, color: C.muted }}>voz sofia · 24 kHz · mono</div>
            </div>
            <div style={{ flex: 1 }} />
            <div style={{ width: 58, height: 58, borderRadius: 29, background: playing ? C.accent : C.surface2, display: "grid", placeItems: "center" }}>
              <Icon name="speaker" size={30} color={playing ? "#fff" : C.ink2} />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 3, height: 90, marginTop: 18 }}>
            {barras.barras.map((b, i) => (
              <div key={i} style={{ flex: 1, height: 8 + b * 78, borderRadius: 3, background: i / barras.barras.length < play ? C.accent : C.line2 }} />
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontFamily: F.mono, fontSize: 18, color: C.muted, marginTop: 6 }}>
            <span>{(play * barras.segundos).toFixed(1).replace(".", ",")} s</span><span>3,0 s</span>
          </div>
        </Card>
      </Pop>
      <Pop at={4.0} style={{ left: 1190, top: 600, width: 630 }}>
        <Card style={{ padding: "14px 22px" }}>
          {[
            ["GET /voices", "41 voces: 28 de mujer, 13 de hombre"],
            ['"response_format": "pcm"', "streaming: primer audio a los 53 ms*"],
          ].map(([a, b]) => (
            <div key={a} style={{ padding: "8px 0", borderTop: a === "GET /voices" ? "none" : `2px solid ${C.line}` }}>
              <div style={{ fontFamily: F.mono, fontSize: 20, color: C.accent2 }}>{a}</div>
              <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 23, color: C.ink }}>{b}</div>
            </div>
          ))}
        </Card>
        <Nota p={1} style={{ marginTop: 8 }}>* medido en el servidor el 9-oct-2026; desde tu red se suma la ida y vuelta</Nota>
      </Pop>
      <div style={{ position: "absolute", left: 100, top: 640, opacity: useIn(4.6) }}>
        <PlanBadge>Todos los planes · minutos de síntesis por mes</PlanBadge>
      </div>
      <Nota p={useIn(4.8)} style={{ position: "absolute", left: 100, top: 700 }}>El audio que se escucha es el que devolvió este pedido.</Nota>
    </AbsoluteFill>
  );
};

const FIELDS = ["especialidad", "turno", "nombre", "dni", "obra_social", "confirma"];

/** 5. API de plataforma: GET de un agente. */
export const Agente: React.FC = () => {
  const card = usePop(2.0);
  const fs = FIELDS.map((_, i) => usePop(5.2 + i * 0.22));
  return (
    <AbsoluteFill>
      <Headline eyebrow="Demo 3 · API de plataforma" text="Consultá un agente," accent="con una key calls." />
      <Pop at={0.2} style={{ left: 100, top: 260, width: 1080 }}>
        <CodeWindow tab="curl" method="GET" path="/api/v1/agents/{id}" status={<Ok>200 OK</Ok>} fontSize={19}>
          <Code text={AGENT} at={0.4} stagger={0.03} hl={[{ a: 2.8, b: 5.0, lines: [4, 5] }, { a: 5.1, b: 8.6, lines: [9, 10, 11, 12, 13, 14, 15] }]} />
        </CodeWindow>
      </Pop>
      <div style={{ position: "absolute", left: 1240, top: 280, width: 580, transform: `scale(${card})`, transformOrigin: "50% 0%" }}>
        <Card style={{ padding: "24px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <AgenteLogo size={86} />
            <div>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ink }}>Turnos</div>
              <div style={{ fontFamily: F.mono, fontSize: 20, color: C.muted }}>v2 · classic · voz sofia</div>
            </div>
          </div>
          <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.accent, margin: "20px 0 10px" }}>DATOS QUE TOMA</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {FIELDS.map((x, i) => (
              <div key={x} style={{ fontFamily: F.mono, fontSize: 21, background: C.accentSoft, color: C.accent2, borderRadius: 10, padding: "6px 12px",
                transform: `scale(${fs[i]})` }}>{x}</div>
            ))}
          </div>
        </Card>
        <Nota p={useIn(3.0)} style={{ marginTop: 12 }}>Agente de la demo de la landing · respuesta real, recortada</Nota>
      </div>
    </AbsoluteFill>
  );
};

/** 6. POST /calls: con teléfono (plan con telefonía) o de prueba; la respuesta trae el conversation_id. */
export const Llamada: React.FC = () => {
  const t = useT();
  const test = t > 3.4;
  const res = usePop(6.2);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Demo 4 · Llamadas" text="Lanzá una llamada" accent="y guardá su id." />
      <Pop at={0.2} style={{ left: 100, top: 260, width: 820 }}>
        <CodeWindow tab="con teléfono · ejemplo de la documentación" method="POST" path="/api/v1/calls" fontSize={20}
          style={{ opacity: test ? 0.55 : 1 }}>
          <Code text={CALL_PHONE} at={0.4} hl={[{ a: 1.6, b: 3.4, lines: [1, 2] }]} />
        </CodeWindow>
        <div style={{ marginTop: 12, opacity: useIn(1.8) }}>
          <PlanBadge>Llamada telefónica: Mostrador, Sucursal y Red (Free no)</PlanBadge>
        </div>
      </Pop>
      <Pop at={3.4} style={{ left: 100, top: 625, width: 820 }}>
        <CodeWindow tab="sin teléfono: prueba" method="POST" path="/api/v1/calls" fontSize={20}>
          <Code text={CALL_TEST} at={3.6} />
        </CodeWindow>
        <Nota p={useIn(4.4)} style={{ marginTop: 10 }}>La que corrimos: no llama a nadie; se atiende desde el navegador</Nota>
      </Pop>
      <div style={{ position: "absolute", left: 980, top: 400, width: 840, transform: `scale(${res})`, transformOrigin: "0% 50%", opacity: Math.min(1, res * 1.4) }}>
        <CodeWindow tab="respuesta" status={<Ok>201 Created</Ok>} method="POST" path="/api/v1/calls" fontSize={20}>
          <Code text={CALL_OUT} at={6.3} hl={[{ a: 7.0, b: 10.4, lines: [1] }]} />
        </CodeWindow>
        <Nota p={useIn(7.4)} style={{ marginTop: 10 }}>Respuesta real · join_url con su token, recortada</Nota>
      </div>
    </AbsoluteFill>
  );
};

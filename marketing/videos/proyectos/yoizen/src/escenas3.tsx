import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { Card, Headline, Icon, useIn, usePop } from "../../../src/comun/ui";

// Todo existe en la API (app/api/routers): rutas reales, recortadas
const DATA = [
  { ep: "GET /calls/{id}", title: "Conversación completa", desc: "Transcripción, datos tomados, resultado y latencia por turno", icon: "users" },
  { ep: "GET /stats", title: "Métricas", desc: "Objetivo cumplido, minutos y tiempo de respuesta", icon: "clock" },
  { ep: "GET /calls/{id}/recordings/{n}", title: "Grabaciones", desc: "Audio por mensaje, si el agente lo activa", icon: "speaker" },
  { ep: "GET /campaigns/{id}/report.csv", title: "Reportes", desc: "Resultado por contacto de cada campaña", icon: "calendar" },
  { ep: "callback_url", title: "Webhook firmado", desc: "Un POST con HMAC por contacto y al cerrar la campaña", icon: "web" },
  { ep: "GET /agents/{id}/versions", title: "Configuración versionada", desc: "Cada cambio es una versión; cada llamada guarda la suya", icon: "check" },
  { ep: "/clients/{id}/llm-connections", title: "LLM: el nuestro o el suyo", desc: "OpenAI compatible, OpenRouter o Anthropic, por agente", icon: "ear" },
  { ep: "API keys", title: "Una llave por sistema", desc: "Con alcance (calls, llm, stt, tts) y revocable al instante", icon: "phone" },
] as const;

/** 5. Acceso completo a datos y configuración. */
export const Datos: React.FC = () => {
  const pops = DATA.map((_, i) => usePop(0.6 + i * 0.32));
  const stat = usePop(4.6);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Sus datos" text="Acceso completo," accent="por API o desde el panel." />
      <div style={{ position: "absolute", left: 110, top: 280, width: 1700, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 22 }}>
        {DATA.map((d, i) => (
          <Card key={d.title} style={{ padding: "20px 22px", height: 236, transform: `scale(${pops[i]})` }}>
            <div style={{ width: 52, height: 52, borderRadius: 14, background: C.accentSoft, display: "grid", placeItems: "center" }}>
              <Icon name={d.icon} size={30} color={C.accent} />
            </div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 27, color: C.ink, marginTop: 12, lineHeight: 1.1 }}>{d.title}</div>
            <div style={{ fontFamily: F.body, fontSize: 19, color: C.muted, marginTop: 6, lineHeight: 1.3 }}>{d.desc}</div>
            <div style={{ fontFamily: F.mono, fontSize: 15, color: C.accent, marginTop: 10, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{d.ep}</div>
          </Card>
        ))}
      </div>
      <div style={{
        position: "absolute", left: 110, top: 840, width: 1700, display: "flex", alignItems: "center", gap: 18, transform: `scale(${stat})`, transformOrigin: "0% 50%",
        background: C.ink, borderRadius: 22, padding: "18px 28px",
      }}>
        <Icon name="clock" size={36} color={C.accentOnDark} />
        <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: "#fff" }}>0,9 s</span>
        <span style={{ fontFamily: F.body, fontSize: 24, color: C.ctaMuted }}>
          mediana del tiempo de respuesta en llamadas reales, de fin de la frase al primer audio del agente
        </span>
      </div>
    </AbsoluteFill>
  );
};

const OPERA = ["Telefonía, números y SIP", "GPUs e inferencia propia", "Modelos y 41 voces", "Escala, monitoreo y soporte"];
const INTEGRA = ["Sus bots y flujos no-code", "Sus canales digitales", "Sus clientes", "Sus datos, siempre accesibles"];

/** 6. Quién hace qué, y cierre con la marca. */
export const Cierre: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const left = OPERA.map((_, i) => useIn(0.5 + i * 0.3, 0.3));
  const right = INTEGRA.map((_, i) => useIn(3.4 + i * 0.3, 0.3));
  const cardL = usePop(0.3);
  const cardR = usePop(3.2);
  const dark = interpolate(t, [6.9, 7.4], [0, 1], CLAMP);
  const logo = usePop(7.3);
  const line = useIn(7.7, 0.6);
  const next = useIn(8.3, 0.5);
  const List: React.FC<{ items: string[]; ps: number[]; ours?: boolean }> = ({ items, ps, ours }) => (
    <>
      {items.map((x, i) => (
        <div key={x} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 0", borderTop: `2px solid ${C.line}`, fontFamily: F.body, fontWeight: 600, fontSize: 27, color: C.ink, opacity: ps[i], transform: `translateX(${(1 - ps[i]) * 16}px)` }}>
          <Icon name="check" size={28} color={ours ? C.accent : C.ok} /> {x}
        </div>
      ))}
    </>
  );
  return (
    <AbsoluteFill>
      <Headline eyebrow="Modelo de operación" text="Nosotros operamos," accent="ustedes integran." />
      <Card style={{ position: "absolute", left: 110, top: 300, width: 620, padding: "24px 30px", transform: `scale(${cardL})`, borderColor: C.accent }}>
        <div style={{ fontFamily: F.mono, fontSize: 19, letterSpacing: "0.08em", color: C.accent }}>ATENTINA OPERA</div>
        <div style={{ height: 10 }} />
        <List items={OPERA} ps={left} ours />
      </Card>
      <Card style={{ position: "absolute", left: 1190, top: 300, width: 620, padding: "24px 30px", transform: `scale(${cardR})`, background: "#fbfcfe", borderColor: C.line2 }}>
        <div style={{ fontFamily: F.mono, fontSize: 19, letterSpacing: "0.08em", color: C.muted }}>YOIZEN INTEGRA</div>
        <div style={{ height: 10 }} />
        <List items={INTEGRA} ps={right} />
      </Card>
      <div style={{ position: "absolute", left: 960 - 120, top: 420 }}>
        <Mascot size={300} />
      </div>
      <Person {...CAST.integrador} size={330} pose="laptop" mood="happy" style={{ position: "absolute", left: 1350, top: 760 }} />

      {/* Cierre oscuro */}
      <AbsoluteFill style={{ background: C.ink, opacity: dark }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 250, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
          <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 620 }} />
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 440, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 64, lineHeight: 1.1, color: C.ctaInk, opacity: line, letterSpacing: "-0.015em" }}>
          Voz administrada,<br /><span style={{ color: C.accentOnDark }}>integrada a lo que ya tienen.</span>
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 660, textAlign: "center", fontFamily: F.mono, fontSize: 28, color: C.ctaMuted, opacity: next }}>
          Próximo paso: un piloto con un caso real · atentina.com.ar
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

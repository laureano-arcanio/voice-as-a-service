import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Mascot } from "../../../src/comun/characters";
import { CodeLine, CodeWindow, Ok, Typed } from "../../../src/comun/code";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, Icon, Pill, useIn, usePop, Wave } from "../../../src/comun/ui";

// API de inferencia (docs/API_INFERENCIA.md): SDK de OpenAI con la base_url de Atentina, recortado
const PY = `from openai import OpenAI
client = OpenAI(base_url=ATENTINA_URL, api_key=ATENTINA_KEY)

# Transcribir una llamada
texto = client.audio.transcriptions.create(model="atentina",
    file=open("llamada-0142.wav", "rb"), language="es").text

# Generar voz
audio = client.audio.speech.create(model="atentina",
    voice="sofia", input="Tu reclamo quedó registrado.")`;

/** 2. API: transcripción y síntesis desde sus sistemas, con el SDK de OpenAI. */
export const Api: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const win = usePop(0.3);
  const compat = usePop(2.0);
  const stt = usePop(4.0);
  const tts = usePop(5.6);
  const voces = usePop(6.6);
  return (
    <AbsoluteFill>
      <Headline eyebrow="API" text="Transcripción y voz" accent="desde tus sistemas." />
      <div style={{ position: "absolute", left: 120, top: 330, width: 1060, transform: `scale(${win})`, transformOrigin: "50% 0%" }}>
        <CodeWindow tab="call_center.py" fontSize={21} minHeight={400}>
          <Typed text={PY} a={0.8} b={5.4} t={t} base={C.ctaInk} />
        </CodeWindow>
        <Pill bg={C.okSoft} fg={C.ok} style={{ marginTop: 22, fontSize: 24, transform: `scale(${compat})`, transformOrigin: "0% 50%" }}>
          <Icon name="check" size={24} /> Compatible con el SDK de OpenAI
        </Pill>
      </div>

      {/* Respuestas */}
      <div style={{ position: "absolute", left: 1240, top: 330, width: 560, display: "flex", flexDirection: "column", gap: 24 }}>
        <div style={{ transform: `scale(${stt})`, transformOrigin: "0% 50%" }}>
          <CodeWindow tab="respuesta" method="POST" path="/audio/transcriptions" status={<Ok>200</Ok>} fontSize={19}>
            <CodeLine line={'{"text": "Buenas tardes, te habla'} />
            <CodeLine line={'  Martín. ¿En qué te puedo…"}'} />
          </CodeWindow>
        </div>
        <div style={{ transform: `scale(${tts})`, transformOrigin: "0% 50%" }}>
          <CodeWindow tab="respuesta" method="POST" path="/audio/speech" status={<Ok>200</Ok>} fontSize={19}>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ background: C.accent, borderRadius: 999, padding: "8px 18px" }}><Wave n={9} h={26} /></div>
              <span style={{ color: C.ctaMuted }}>audio · voz "sofia"</span>
            </div>
          </CodeWindow>
        </div>
        <Card style={{ padding: "18px 22px", display: "flex", alignItems: "center", gap: 16, transform: `scale(${voces})`, transformOrigin: "0% 50%" }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: C.accentSoft, display: "grid", placeItems: "center" }}>
            <Icon name="speaker" size={30} color={C.accent} />
          </div>
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>41 voces argentinas</div>
            <div style={{ fontFamily: F.body, fontSize: 20, color: C.muted }}>Para IVR, avisos y respuestas</div>
          </div>
        </Card>
      </div>
    </AbsoluteFill>
  );
};

const NODOS = [
  { x: 360, icon: "phone" as const, title: "Tu central", sub: "Llamadas en curso" },
  { x: 960, icon: "ear" as const, title: "Atentina", sub: "Voz a texto y datos", ours: true },
  { x: 1560, icon: "users" as const, title: "Tu CRM", sub: "Tickets y reportes" },
];
const NW = 400;
const NY = 400;

const SENT = [
  { quien: "Cliente", v: "Molesto", c: C.warn, bg: C.warnSoft },
  { quien: "Cliente", v: "Conforme", c: C.ok, bg: C.okSoft },
];

/** 3. Integración a medida: tiempo real, sentimiento y extracción de datos. */
export const Integracion: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const nodos = NODOS.map((_, i) => usePop(0.3 + i * 0.3));
  const cards = [usePop(2.4), usePop(4.0), usePop(5.6)];
  const nota = useIn(6.8, 0.5);
  // Un paquete por ciclo de 2,4 s: voz de la central a Atentina, texto de Atentina al CRM
  const cyc = t < 1.4 ? -1 : (t - 1.4) % 2.4;
  const tramo = cyc < 0 ? -1 : cyc < 1.0 ? 0 : cyc < 2.0 ? 1 : -1;
  const k = tramo < 0 ? 0 : interpolate(tramo === 0 ? cyc : cyc - 1.0, [0, 0.9], [0, 1], { ...CLAMP, easing: EASE });
  const a = tramo === 1 ? NODOS[1].x + NW / 2 : NODOS[0].x + NW / 2;
  const b = tramo === 1 ? NODOS[2].x - NW / 2 : NODOS[1].x - NW / 2;
  const px = a + (b - a) * k;
  const activo = (i: number) => (tramo === 0 && i === 1 && k > 0.85) || (tramo === 1 && (i === 1 && k < 0.2 || i === 2 && k > 0.85));
  // Sentimiento que cambia a lo largo de la llamada
  const sent = t < 4.9 ? 0 : 1;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Integración" text="Conectado a tus sistemas," accent="a tu medida." />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d={`M${NODOS[0].x + NW / 2} ${NY} H${NODOS[2].x - NW / 2}`} stroke={C.line2} strokeWidth={5} strokeDasharray="2 14" strokeLinecap="round" opacity={nodos[2]} />
      </svg>
      {NODOS.map((n, i) => {
        const on = activo(i);
        return (
          <Card key={n.title} style={{
            position: "absolute", left: n.x - NW / 2, top: NY - 70, width: NW, height: 140, padding: "22px 24px", boxSizing: "border-box",
            display: "flex", alignItems: "center", gap: 16, transform: `scale(${nodos[i] * (on ? 1.04 : 1)})`,
            borderColor: n.ours || on ? C.accent : C.line2, background: n.ours ? "#fff" : "#fbfcfe",
            boxShadow: on ? "0 18px 44px rgba(36,86,230,.25)" : shadowCard,
          }}>
            {n.ours ? (
              <div style={{ width: 80, height: 80, display: "grid", placeItems: "center" }}><Mascot size={84} bodyless /></div>
            ) : (
              <div style={{ width: 64, height: 64, borderRadius: 16, background: C.surface2, display: "grid", placeItems: "center" }}>
                <Icon name={n.icon} size={36} color={C.ink2} />
              </div>
            )}
            <div>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>{n.title}</div>
              <div style={{ fontFamily: F.body, fontSize: 21, color: C.muted }}>{n.sub}</div>
            </div>
          </Card>
        );
      })}
      {tramo >= 0 ? (
        <div style={{
          position: "absolute", left: px, top: NY - 104, transform: "translate(-50%, -50%)", background: tramo === 1 ? C.ink : C.accent, color: "#fff",
          borderRadius: 999, padding: "8px 16px", fontFamily: F.mono, fontSize: 20, boxShadow: "0 10px 26px rgba(36,86,230,.3)",
        }}>
          {tramo === 1 ? "Aa" : <Wave n={5} h={22} />}
        </div>
      ) : null}

      {/* Lo que se suma */}
      <div style={{ position: "absolute", left: 160, top: 570, width: 1600, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 28 }}>
        <Card style={{ padding: "22px 26px", height: 250, boxSizing: "border-box", transform: `scale(${cards[0]})` }}>
          <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.accent }}>EN TIEMPO REAL</div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, marginTop: 6 }}>Transcripción en vivo</div>
          <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ width: 12, height: 12, borderRadius: 6, background: C.warn, opacity: Math.floor(frame / 15) % 2 ? 0.35 : 1 }} />
            <span style={{ fontFamily: F.mono, fontSize: 18, color: C.muted }}>En curso · 01:24</span>
          </div>
          <div style={{ fontFamily: F.body, fontSize: 22, color: C.ink2, marginTop: 10, lineHeight: 1.35 }}>
            <b style={{ color: C.ink }}>Cliente:</b> {"me cobraron dos veces el mismo mes".slice(0, Math.floor(interpolate(t, [2.8, 4.4], [0, 34], CLAMP)))}
          </div>
        </Card>
        <Card style={{ padding: "22px 26px", height: 250, boxSizing: "border-box", transform: `scale(${cards[1]})` }}>
          <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.accent }}>SENTIMIENTO</div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, marginTop: 6 }}>Cómo está el cliente</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 24 }}>
            {SENT.map((s, i) => (
              <React.Fragment key={s.v}>
                {i > 0 ? <span style={{ fontFamily: F.mono, fontSize: 24, color: C.muted }}>→</span> : null}
                <Pill bg={s.bg} fg={s.c} style={{ fontSize: 22, padding: "8px 18px", opacity: i <= sent ? 1 : 0.25 }}>{s.v}</Pill>
              </React.Fragment>
            ))}
          </div>
          <div style={{ fontFamily: F.body, fontSize: 20, color: C.muted, marginTop: 18 }}>Al inicio y al final de la llamada</div>
        </Card>
        <Card style={{ padding: "22px 26px", height: 250, boxSizing: "border-box", transform: `scale(${cards[2]})` }}>
          <div style={{ fontFamily: F.mono, fontSize: 18, letterSpacing: "0.08em", color: C.accent }}>EXTRACCIÓN DE DATOS</div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink, marginTop: 6 }}>Directo a tu CRM</div>
          <div style={{ marginTop: 14, background: C.ink, borderRadius: 14, padding: "12px 16px", fontFamily: F.mono, fontSize: 19, lineHeight: 1.5, whiteSpace: "pre" }}>
            <Typed text={'{"cliente": "48213",\n "motivo": "cargo duplicado",\n "resuelto": true}'} a={5.8} b={7.0} t={t} />
          </div>
        </Card>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 850, textAlign: "center", fontFamily: F.mono, fontSize: 21, color: C.muted, opacity: nota }}>
        Integración a medida, con nuestros motores de transcripción, lenguaje y voz
      </div>
    </AbsoluteFill>
  );
};

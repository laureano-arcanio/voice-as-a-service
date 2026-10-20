import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { level, RESPUESTA, VIAJE as V } from "./timeline";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Card, Eyebrow, Headline, Icon, Pill, useIn, usePop, Wave } from "../../../src/comun/ui";

const LINE_Y = 480;
const RET_Y = 905;
const CLIENT_X = 200;
const NODES = [
  { x: 560, tag: "Canal", title: "Llamada", sub: "Teléfono · WhatsApp · Web", icon: "phone" as const },
  { x: 900, tag: "STT", title: "Escucha", sub: "Reconocimiento de voz", icon: "ear" as const },
  { x: 1240, tag: "LLM", title: "Piensa", sub: "Agente de IA", icon: null },
  { x: 1580, tag: "TTS", title: "Responde", sub: "Síntesis de voz", icon: "speaker" as const },
];
const CW = 304;
const CH = 220;
const LOW_Y = 660; // fila de abajo: CRM y cronómetro

const lin = (t: number, a: number, b: number, x0: number, x1: number) => interpolate(t, [a, b], [x0, x1], CLAMP);

/** Recorrido de la respuesta: TTS → abajo → izquierda → arriba hasta la cliente, u en 0..1 (sin volver sobre sus pasos). */
const returnPoint = (u: number): [number, number] => {
  const pts: [number, number][] = [[NODES[3].x, LINE_Y + CH / 2], [NODES[3].x, RET_Y], [CLIENT_X, RET_Y], [CLIENT_X, 640]];
  const lens = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
  let d = u * lens.reduce((a, b) => a + b, 0);
  for (let i = 0; i < lens.length; i++) {
    if (d <= lens[i] || i === lens.length - 1) {
      const k = Math.min(1, d / lens[i]);
      return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k];
    }
    d -= lens[i];
  }
  return pts[pts.length - 1];
};

type Pos = { x: number; y: number; kind: "wave" | "text" | "tool" };

/** Dónde está el paquete en el instante t (ida por la línea, ida y vuelta al CRM). */
const packetAt = (t: number): Pos | null => {
  if (t >= V.C1 && t < V.END_C1) return { x: lin(t, V.C1, V.END_C1, CLIENT_X + 110, NODES[1].x), y: LINE_Y, kind: "wave" };
  if (t >= V.END_C1 && t < V.LLM) return { x: lin(t, V.END_C1, V.LLM, NODES[1].x, NODES[2].x), y: LINE_Y, kind: "text" };
  if (t >= V.LLM + 0.04 && t < V.CRM) return { x: NODES[2].x, y: lin(t, V.LLM + 0.04, V.CRM, LINE_Y + CH / 2, LOW_Y), kind: "tool" };
  if (t >= V.CRM + 0.06 && t < V.CRM_BACK) return { x: NODES[2].x, y: lin(t, V.CRM + 0.06, V.CRM_BACK, LOW_Y, LINE_Y + CH / 2), kind: "tool" };
  if (t >= V.CRM_BACK + 0.04 && t < V.TTS) return { x: lin(t, V.CRM_BACK + 0.04, V.TTS, NODES[2].x, NODES[3].x), y: LINE_Y, kind: "text" };
  return null;
};

const Packet: React.FC<{ p: Pos; ghost?: number }> = ({ p, ghost = 1 }) => (
  <div style={{
    position: "absolute", left: p.x, top: p.y, transform: "translate(-50%, -50%)", opacity: ghost,
    background: p.kind === "wave" ? C.accent : p.kind === "tool" ? C.ok : C.ink, borderRadius: 999, padding: "12px 20px",
    boxShadow: ghost === 1 ? "0 10px 26px rgba(36,86,230,.35)" : "none", fontFamily: F.mono, fontSize: 24, color: "#fff",
  }}>
    {p.kind === "wave" ? <Wave n={6} h={28} /> : p.kind === "tool" ? "{ }" : "Aa"}
  </div>
);

/** 3. Cómo viaja la voz: cliente → canal → STT → LLM (+ CRM) → TTS → cliente, en menos de un segundo. */
export const Viaje: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const bracket = useIn(0.6, 0.5);
  const lineIn = useIn(0.2, 0.5);
  const retIn = useIn(0.4, 0.5);
  const lowIn = usePop(0.5);
  const pops = [usePop(0.1), usePop(0.22), usePop(0.34), usePop(0.46)];
  const heard = useIn(V.STT, 0.15);
  const slots = useIn(V.CRM, 0.12);

  const packet = packetAt(t);
  // Estela: el mismo paquete unos frames antes, para que se note la velocidad
  const trail = [2, 4].map((k) => packetAt((frame - k) / fps));
  // La respuesta viaja de vuelta mientras Atentina habla, con aceleración suave
  const back = t >= V.A1 && t < V.END_A1
    ? returnPoint(interpolate(t, [V.A1, V.END_A1], [0, 1], { ...CLAMP, easing: Easing.inOut(Easing.cubic) }))
    : null;

  const active = (i: number) => {
    if (i === 0) return t > V.C1 + 0.3 && t < V.C1 + 1.2;
    if (i === 1) return t > V.END_C1 - 0.3 && t < V.STT + 0.08;
    if (i === 2) return t >= V.LLM - 0.04 && t < V.CRM_BACK + 0.1;
    return t >= V.TTS - 0.06 && t < V.A1 + 0.5;
  };
  const crmOn = t >= V.CRM - 0.04 && t < V.CRM_BACK;

  // Cronómetro: corre en tiempo real desde que la cliente termina de hablar hasta la respuesta
  const clock = Math.max(0, Math.min(RESPUESTA, t - V.END_C1));
  const clockDone = t >= V.A1;
  const flash = interpolate(t, [V.A1, V.A1 + 0.15, V.A1 + 0.6], [0, 1, 0], CLAMP);

  return (
    <AbsoluteFill>
      <Headline eyebrow="Cómo viaja la voz" text="Escucha, consulta y responde" accent="al instante." size={58} />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d={`M${CLIENT_X + 100} ${LINE_Y} H${NODES[3].x}`} stroke={C.line2} strokeWidth={5} strokeDasharray="2 14" strokeLinecap="round" opacity={lineIn} />
        <path d={`M${NODES[3].x} ${LINE_Y + CH / 2} V${RET_Y} H${CLIENT_X} V640`} stroke={C.line2} strokeWidth={5} strokeDasharray="2 14"
          strokeLinecap="round" fill="none" opacity={retIn} />
        <path d={`M${NODES[2].x} ${LINE_Y + CH / 2} V${LOW_Y}`} stroke={crmOn ? C.ok : C.line2} strokeWidth={5} strokeDasharray="2 14" strokeLinecap="round" opacity={retIn} />
      </svg>
      <div style={{ position: "absolute", left: 640, top: RET_Y + 16, fontFamily: F.mono, fontSize: 20, color: C.muted, letterSpacing: "0.06em", textTransform: "uppercase", opacity: retIn }}>
        La respuesta vuelve por el mismo canal
      </div>

      {/* Llave sobre las etapas de IA */}
      <div style={{ position: "absolute", left: NODES[1].x - CW / 2, width: NODES[3].x - NODES[1].x + CW, top: 262, opacity: bracket }}>
        <div style={{ textAlign: "center" }}><Eyebrow>Inferencia propia · servidores en Argentina</Eyebrow></div>
        <div style={{ height: 20, marginTop: 10, borderTop: `4px solid ${C.accent}`, borderLeft: `4px solid ${C.accent}`, borderRight: `4px solid ${C.accent}`, borderRadius: "14px 14px 0 0" }} />
      </div>

      {/* La cliente */}
      <div style={{ position: "absolute", left: CLIENT_X - 100, top: 296, width: 200, textAlign: "center", fontFamily: F.display, fontWeight: 700, fontSize: 30, color: C.ink }}>Cliente</div>
      <div style={{ position: "absolute", left: CLIENT_X - 145, top: 350, width: 290, height: 290, borderRadius: "50%", background: C.accentSoft }} />
      <Person {...CAST.cliente} size={340} pose="phone" mood={t > V.END_A1 ? "happy" : "neutral"} talk={level("c1", frame, V.C1)}
        style={{ position: "absolute", left: CLIENT_X - 136, top: 330 }} />

      {/* Nodos */}
      {NODES.map((n, i) => {
        const on = active(i);
        return (
          <Card key={n.tag} style={{
            position: "absolute", left: n.x - CW / 2, top: LINE_Y - CH / 2, width: CW, height: CH, padding: 24,
            transform: `scale(${pops[i] * (on ? 1.06 : 1)})`, borderColor: on ? C.accent : C.line,
            boxShadow: on ? "0 18px 44px rgba(36,86,230,.25)" : shadowCard,
          }}>
            <div style={{ position: "absolute", right: 20, top: 20, fontFamily: F.mono, fontSize: 18, color: C.muted, letterSpacing: "0.06em" }}>{n.tag.toUpperCase()}</div>
            <div style={{ width: 80, height: 80, borderRadius: 22, background: on ? C.accent : C.accentSoft, display: "grid", placeItems: "center" }}>
              {n.icon ? <Icon name={n.icon} size={44} color={on ? "#fff" : C.accent} /> : <Mascot size={70} bodyless talk={level("a1", frame, V.A1)} />}
            </div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 36, color: C.ink, marginTop: 14 }}>{n.title}</div>
            <div style={{ fontFamily: F.body, fontWeight: 500, fontSize: 20, color: C.muted, marginTop: 2, whiteSpace: "nowrap" }}>{n.sub}</div>
          </Card>
        );
      })}

      {/* Lo que entendió */}
      <Pill bg="#fff" fg={C.ink} style={{ position: "absolute", left: NODES[1].x - CW / 2, top: LINE_Y + CH / 2 + 26, opacity: heard, border: `2px solid ${C.line}`, fontWeight: 600, fontSize: 23, padding: "10px 18px" }}>
        <span style={{ fontFamily: F.mono, fontSize: 17, color: C.muted }}>TEXTO</span> “Quería hacer una consulta”
      </Pill>

      {/* Los sistemas del negocio (CRM) */}
      <Card style={{
        position: "absolute", left: NODES[2].x - CW / 2, top: LOW_Y, width: CW, height: 168, padding: 20, transform: `scale(${lowIn * (crmOn ? 1.06 : 1)})`,
        borderColor: crmOn ? C.ok : C.line, boxShadow: crmOn ? "0 18px 44px rgba(27,156,91,.25)" : shadowCard,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 60, height: 60, borderRadius: 18, background: crmOn ? C.ok : C.okSoft, display: "grid", placeItems: "center" }}>
            <Icon name="users" size={36} color={crmOn ? "#fff" : C.ok} />
          </div>
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 27, color: C.ink, whiteSpace: "nowrap" }}>CRM</div>
            <div style={{ fontFamily: F.body, fontWeight: 500, fontSize: 19, color: C.muted }}>Tus sistemas</div>
          </div>
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 20, color: C.ok, marginTop: 14, opacity: slots, whiteSpace: "nowrap" }}>→ Carolina Pérez</div>
      </Card>
      <div style={{ position: "absolute", left: NODES[2].x + 16, top: LINE_Y + CH / 2 + 18, fontFamily: F.mono, fontSize: 19, color: C.ok, opacity: useIn(V.LLM, 0.1) }}>
        buscar_cliente(teléfono)
      </div>

      {/* Cronómetro */}
      <Card style={{
        position: "absolute", left: NODES[0].x - CW / 2, top: LOW_Y, width: CW, height: 168, padding: 20, transform: `scale(${lowIn})`,
        borderColor: clockDone ? C.accent : C.line, boxShadow: `0 0 0 ${flash * 14}px rgba(36,86,230,${0.25 * flash}), ${shadowCard}`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: F.mono, fontSize: 16, color: C.muted, letterSpacing: "0.04em", whiteSpace: "nowrap" }}>
          <Icon name="clock" size={22} color={C.muted} /> TIEMPO DE RESPUESTA
        </div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 56, lineHeight: 1.1, color: clock > 0 ? C.accent : C.line2, marginTop: 6, fontVariantNumeric: "tabular-nums" }}>
          {clock.toFixed(2).replace(".", ",")} s
        </div>
        <div style={{ fontFamily: F.body, fontSize: 17, color: C.muted, opacity: useIn(V.A1 + 0.3, 0.3) }}>Mediana en llamadas reales</div>
      </Card>

      {/* Paquetes, con estela */}
      {trail.map((p, i) => (p ? <Packet key={i} p={p} ghost={0.35 - i * 0.15} /> : null))}
      {packet ? <Packet p={packet} /> : null}
      {back ? (
        <div style={{ position: "absolute", left: back[0], top: back[1], transform: "translate(-50%, -50%)", background: C.accent, borderRadius: 999, padding: "12px 20px", boxShadow: "0 10px 26px rgba(36,86,230,.35)" }}>
          <Wave n={6} h={28} />
        </div>
      ) : null}

      <Subtitle t={t} />
    </AbsoluteFill>
  );
};

const Subtitle: React.FC<{ t: number }> = ({ t }) => {
  const lines = [
    { from: V.C1, to: V.END_C1 + 0.3, who: "Cliente", text: "Hola, quería hacer una consulta." },
    { from: V.A1, to: V.END_A1 + 0.5, who: "Atentina", text: "¡Hola, Carolina! Ya tengo tu cuenta abierta. ¿En qué te ayudo?" },
  ];
  const l = lines.find((x) => t >= x.from && t < x.to);
  if (!l) return null;
  const o = Math.min(1, (t - l.from) * 6, (l.to - t) * 5);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 975, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{ background: C.ink, color: "#fff", borderRadius: 18, padding: "14px 28px", fontFamily: F.body, fontSize: 32, fontWeight: 500 }}>
        <span style={{ fontFamily: F.mono, fontSize: 22, color: l.who === "Atentina" ? C.accentOnDark : C.ctaMuted, marginRight: 16, letterSpacing: "0.06em" }}>
          {l.who.toUpperCase()}
        </span>
        {l.text}
      </div>
    </div>
  );
};

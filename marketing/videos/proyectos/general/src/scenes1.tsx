import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Bubble, Card, Headline, Icon, Link, Pill, useIn, usePop } from "../../../src/comun/ui";

// Los tres que llaman, cada uno por un canal: posición del personaje y del dispositivo (para las líneas)
const CALLERS = [
  { cast: CAST.cliente, pose: "phone" as const, x: 40, y: 600, size: 360, dev: [80, 700], say: "Llamando…", ch: "phone" as const },
  { cast: CAST.cliente2, pose: "texting" as const, x: 340, y: 650, size: 340, dev: [530, 900], say: "Una consulta…", ch: "wa" as const },
  { cast: CAST.cliente3, pose: "laptop" as const, x: 640, y: 690, size: 320, dev: [790, 960], say: "¿Hola?", ch: "web" as const },
];

/** 1. El problema: varios clientes a la vez contra una sola línea; la dueña está ocupada y se van a la competencia. */
export const Problema: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const lines = useIn(0.5, 0.5);
  const busy = usePop(1.0);
  const lost = t > 2.0;
  const comp = usePop(3.0);
  const toComp = useIn(3.1, 0.6);
  const card = usePop(0.2);
  const minus = interpolate(t, [3.6, 4.0], [0, 1], CLAMP);
  const bubbles = [useIn(0.3, 0.3), useIn(0.55, 0.3), useIn(0.8, 0.3)];
  const ring = Math.sin(frame * 1.6) * (t < 3.0 ? 4 : 0);
  const LINE = [1000, 430];
  const COMP = [1530, 360];
  return (
    <AbsoluteFill>
      <Headline eyebrow="El problema" text="Cada llamada sin atender es un cliente que se va" accent="con la competencia." size={62} />

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {CALLERS.map((c, i) => (
          <Link key={i} d={`M${c.dev[0]} ${c.dev[1] - 150} C ${c.dev[0] + 120} ${c.dev[1] - 360}, ${LINE[0] - 200} ${LINE[1] + 40}, ${LINE[0]} ${LINE[1]}`}
            color={lost ? C.warn : C.accent} opacity={lines * (1 - toComp)} />
        ))}
        {CALLERS.map((c, i) => (
          <Link key={`c${i}`} d={`M${c.dev[0]} ${c.dev[1] - 150} C ${c.dev[0] + 200} ${120 + i * 30}, ${COMP[0] - 300} ${COMP[1] - 80}, ${COMP[0]} ${COMP[1]}`}
            color={C.muted} opacity={toComp} />
        ))}
      </svg>

      {CALLERS.map((c, i) => (
        <React.Fragment key={i}>
          <Person {...c.cast} size={c.size} pose={c.pose} mood={lost ? "sad" : "neutral"} blinkOffset={i * 23}
            style={{ position: "absolute", left: c.x, top: c.y }} />
          <Bubble style={{ left: c.x + c.size * 0.45, top: c.y - 80, opacity: bubbles[i] * (1 - toComp) }} fg={lost ? C.warn : C.ink}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 10, fontSize: 26 }}>
              {lost ? <><Icon name="missed" size={26} /> Sin respuesta</> : <><Icon name={c.ch} size={26} color={c.ch === "wa" ? C.wa : C.accent} /> {c.say}</>}
            </span>
          </Bubble>
        </React.Fragment>
      ))}

      {/* La única línea del negocio */}
      <Card style={{ position: "absolute", left: LINE[0], top: LINE[1] - 80, width: 300, padding: "20px 24px", transform: `scale(${card})` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ transform: `rotate(${ring}deg)`, display: "flex", gap: 8 }}>
            <Icon name="phone" size={36} color={C.ink} />
            <Icon name="wa" size={36} color={C.wa} />
          </div>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>Tu línea</div>
        </div>
        <Pill bg={C.warnSoft} fg={C.warn} style={{ marginTop: 14, fontSize: 22, padding: "6px 16px", transform: `scale(${busy})`, transformOrigin: "left center" }}>
          ● Ocupada · 1 a la vez
        </Pill>
      </Card>

      {/* La dueña, atendiendo a otro cliente en el mostrador */}
      <div style={{ position: "absolute", left: 1330, top: 600, width: 560, height: 420, borderRadius: 40, background: C.surface2 }} />
      <Person {...CAST.duena} size={430} talk={0.25 + 0.25 * Math.sin(frame / 3)} style={{ position: "absolute", left: 1500, top: 600 }} />
      <Person {...CAST.otro} size={330} pose="back" style={{ position: "absolute", left: 1290, top: 780 }} />
      <div style={{ position: "absolute", left: 1230, top: 980, width: 700, height: 120, background: "#fff", borderTop: `6px solid ${C.line2}` }} />

      {/* La competencia */}
      <Card style={{ position: "absolute", left: COMP[0] - 40, top: COMP[1] - 70, width: 380, padding: "18px 22px", transform: `scale(${comp})` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink2 }}>
          <Icon name="store" size={36} color={C.muted} /> <span style={{ whiteSpace: "nowrap" }}>La competencia</span>
        </div>
        <Pill bg={C.okSoft} fg={C.ok} style={{ marginTop: 12, fontSize: 22, padding: "6px 16px" }}>● Atiende</Pill>
      </Card>
      <div style={{ position: "absolute", left: COMP[0] + 10, top: COMP[1] + 110, fontFamily: F.mono, fontSize: 24, color: C.warn, opacity: minus, letterSpacing: "0.04em" }}>
        3 clientes perdidos
      </div>
    </AbsoluteFill>
  );
};

const SERVED = [
  { cast: CAST.cliente, pose: "phone" as const, x: 60, y: 520, size: 360, anchor: [250, 640], chip: { at: 3.0, icon: "phone" as const, label: "Teléfono", color: C.accent } },
  { cast: CAST.cliente2, pose: "texting" as const, x: 1500, y: 520, size: 360, anchor: [1650, 640], chip: { at: 3.9, icon: "wa" as const, label: "WhatsApp", color: C.wa } },
  { cast: CAST.cliente3, pose: "laptop" as const, x: 400, y: 700, size: 330, anchor: [560, 820], chip: { at: 4.6, icon: "web" as const, label: "Web", color: C.accent } },
];

/** 2. Atentina atiende a todos a la vez, por cada canal. */
export const Atentina: React.FC = () => {
  const frame = useCurrentFrame();
  const pop = usePop(0.2);
  const links = useIn(0.8, 0.5);
  const h24 = useIn(1.2, 0.4);
  const chips = [usePop(SERVED[0].chip.at), usePop(SERVED[1].chip.at), usePop(SERVED[2].chip.at)];
  const oks = [usePop(1.0), usePop(1.12), usePop(1.24)];
  const CENTER = [960, 640];
  return (
    <AbsoluteFill>
      <Headline eyebrow="La solución" text="Atentina atiende" accent="a todos a la vez." />
      <Pill bg={C.okSoft} fg={C.ok} style={{ position: "absolute", left: 120, top: 250, fontFamily: F.mono, fontWeight: 500, fontSize: 22, letterSpacing: "0.06em", padding: "8px 18px", opacity: h24 }}>
        ● LAS 24 HORAS
      </Pill>

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {SERVED.map((s, i) => (
          <Link key={i} d={`M${s.anchor[0]} ${s.anchor[1]} Q ${(s.anchor[0] + CENTER[0]) / 2} ${Math.min(s.anchor[1], CENTER[1]) - 120}, ${CENTER[0]} ${CENTER[1]}`}
            color={C.ok} opacity={links} width={6} />
        ))}
      </svg>

      <div style={{ position: "absolute", left: 960 - 300, top: 360, width: 600, height: 600, borderRadius: "50%", background: C.accentSoft, transform: `scale(${pop})` }} />
      <div style={{ position: "absolute", left: 960 - 224, top: 400, transform: `scale(${pop})`, transformOrigin: "50% 100%" }}>
        <Mascot size={560} talk={0.35 + 0.3 * Math.abs(Math.sin(frame / 5))} />
      </div>

      {SERVED.map((s, i) => (
        <React.Fragment key={i}>
          <Person {...s.cast} size={s.size} pose={s.pose} mood="happy" talk={i === 1 ? 0 : 0.2 + 0.2 * Math.sin(frame / 3 + i)} blinkOffset={i * 31}
            style={{ position: "absolute", left: s.x, top: s.y }} />
          <Pill bg={C.okSoft} fg={C.ok} style={{ position: "absolute", left: s.x + 40, top: s.y - 56, fontSize: 22, padding: "6px 16px", transform: `scale(${oks[i]})` }}>
            ● Atendido
          </Pill>
          <Pill bg="#fff" fg={C.ink} style={{
            position: "absolute", left: (s.anchor[0] + CENTER[0]) / 2 - 90, top: Math.min(s.anchor[1], CENTER[1]) - 130,
            transform: `scale(${chips[i]})`, border: `2px solid ${C.line}`, fontSize: 28, boxShadow: shadowCard,
          }}>
            <Icon name={s.chip.icon} size={32} color={s.chip.color} /> {s.chip.label}
          </Pill>
        </React.Fragment>
      ))}
    </AbsoluteFill>
  );
};

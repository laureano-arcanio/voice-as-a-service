import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { AgenteLogo, CAST, Person } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Icon, useIn, usePop } from "../../../src/comun/ui";
import { Titulo, useT } from "./pantalla";

// Diagramas animados: cómo funciona la derivación (ciclo del agente, áreas, espera y si nadie atiende).

const Nota: React.FC<{ x: number; y: number; at: number }> = ({ x, y, at }) => {
  const t = useT();
  const k = ((t - at) % 1.8) / 1.8;
  if (t < at) return null;
  return (
    <div style={{
      position: "absolute", left: x + Math.sin(k * 6) * 10, top: y - k * 90, opacity: Math.sin(k * Math.PI),
      fontSize: 46, color: C.accent, fontFamily: F.body, fontWeight: 800,
    }}>♪</div>
  );
};

/** Persona del equipo o área: busto chico en un círculo, con su número de orden. */
const Cara: React.FC<{ cast: keyof typeof CAST; n?: number; size?: number; ring?: number; dim?: number; style?: React.CSSProperties }> = ({
  cast, n, size = 104, ring = 0, dim = 1, style,
}) => (
  <div style={{ position: "relative", width: size, height: size, opacity: dim, ...style }}>
    <div style={{
      width: size, height: size, borderRadius: size / 2, overflow: "hidden", background: C.accentSoft,
      border: `4px solid ${ring > 0 ? C.accent : "#fff"}`, boxShadow: ring > 0 ? `0 0 0 ${8 * ring}px rgba(36,86,230,.18)` : shadowCard,
    }}>
      <Person {...CAST[cast]} size={size * 1.25} mood="happy" style={{ marginLeft: -size * 0.0, marginTop: -size * 0.02 }} />
    </div>
    {n ? (
      <div style={{
        position: "absolute", right: -6, bottom: -6, width: 38, height: 38, borderRadius: 19, background: C.ink, color: "#fff",
        fontFamily: F.mono, fontSize: 21, display: "flex", alignItems: "center", justifyContent: "center", border: "3px solid #fff",
      }}>{n}</div>
    ) : null}
  </div>
);

// 2. El ciclo del agente: muchas llamadas, escucha, entiende y responde.
export const Ciclo: React.FC = () => {
  const t = useT();
  const frame = useCurrentFrame();
  const people: (keyof typeof CAST)[] = ["cliente", "cliente2", "otro", "cliente3", "integrador"];
  const CX = 540;
  const CY = 1110;
  const R = 300;
  const ring = useIn(2.2, 0.8);
  // Punto que recorre el ciclo: una vuelta cada 3 s desde los 2,6 s
  const ang = t < 2.6 ? -150 : -150 + ((t - 2.6) / 3) * 360;
  const nodes = [
    { a: -150, label: "Escucha", icon: "ear" as const },
    { a: -30, label: "Entiende", icon: null },
    { a: 90, label: "Responde", icon: "speaker" as const },
  ];
  const near = (a: number) => {
    const d = (((ang - a) % 360) + 360) % 360;
    return t >= 2.6 && d < 70 ? 1 - d / 70 : 0;
  };
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Cómo funciona" text="Llaman muchos clientes y el agente" accent="atiende cada llamada." size={58} />
      {people.map((c, i) => {
        const p = usePop(0.4 + i * 0.22);
        const x = 90 + i * 190;
        const flow = interpolate(t, [1.4 + i * 0.12, 2.3 + i * 0.12], [0, 1], { ...CLAMP, easing: EASE });
        return (
          <React.Fragment key={c}>
            <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
              <path d={`M ${x + 70} 560 Q ${x + 70} 700 ${CX} ${CY - 150}`} fill="none" stroke={C.line2} strokeWidth={4}
                strokeDasharray="10 12" strokeDashoffset={-frame * 2} opacity={flow} />
            </svg>
            <div style={{ position: "absolute", left: x, top: 400, transform: `scale(${p})`, transformOrigin: "50% 100%" }}>
              <Cara cast={c} size={140} />
              <div style={{
                position: "absolute", right: -8, top: -8, width: 46, height: 46, borderRadius: 23, background: C.ok,
                display: "flex", alignItems: "center", justifyContent: "center", border: "3px solid #fff",
                transform: `rotate(${Math.sin(frame / 3 + i) * 12}deg)`,
              }}>
                <Icon name="phone" size={24} color="#fff" />
              </div>
            </div>
          </React.Fragment>
        );
      })}
      {/* El ciclo */}
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, opacity: ring }}>
        <circle cx={CX} cy={CY} r={R} fill="none" stroke={C.accentSoft} strokeWidth={18} />
        <circle cx={CX} cy={CY} r={R} fill="none" stroke={C.accent} strokeWidth={5} strokeDasharray="14 16" strokeDashoffset={-frame * 2.5} />
        {t >= 2.6 ? (
          <circle cx={CX + R * Math.cos((ang * Math.PI) / 180)} cy={CY + R * Math.sin((ang * Math.PI) / 180)} r={16} fill={C.accent} />
        ) : null}
      </svg>
      <div style={{ position: "absolute", left: CX - 120, top: CY - 120, transform: `scale(${usePop(1.6)})` }}>
        <AgenteLogo size={240} talk={near(90) * 0.9} />
      </div>
      {nodes.map((n, i) => {
        const p = usePop(2.4 + i * 0.2);
        const k = near(n.a);
        const x = CX + R * Math.cos((n.a * Math.PI) / 180);
        const y = CY + R * Math.sin((n.a * Math.PI) / 180);
        return (
          <div key={n.label} style={{
            position: "absolute", left: x - 130, top: y - 44, width: 260, height: 88, borderRadius: 44,
            background: k > 0.2 ? C.accent : "#fff", color: k > 0.2 ? "#fff" : C.ink, border: `3px solid ${k > 0.2 ? C.accent : C.line}`,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 12, boxShadow: shadowCard,
            fontFamily: F.body, fontWeight: 800, fontSize: 34, transform: `scale(${p * (1 + k * 0.1)})`,
          }}>
            {n.icon ? <Icon name={n.icon} size={34} color={k > 0.2 ? "#fff" : C.accent} /> : (
              <span style={{ fontFamily: F.mono, fontSize: 28, color: k > 0.2 ? "#fff" : C.accent }}>Aa</span>
            )}
            {n.label}
          </div>
        );
      })}
      <div style={{
        position: "absolute", left: 0, right: 0, top: 1560, textAlign: "center", opacity: useIn(4.6, 0.6),
        fontFamily: F.mono, fontSize: 28, letterSpacing: "0.06em", color: C.ink2,
      }}>
        TURNO A TURNO, EN UN CICLO
      </div>
    </AbsoluteFill>
  );
};

type Area = { name: string; desc: string; horario: string; people: { cast: keyof typeof CAST; name: string }[] };
const AREAS: Area[] = [
  { name: "Ventas", desc: "Precios, presupuestos y visitas", horario: "Lun a vie 9 a 18 · sáb 9 a 13",
    people: [{ cast: "duena", name: "Lucía" }, { cast: "integrador", name: "Diego" }] },
  { name: "Soporte técnico", desc: "Equipos que no enfrían, service", horario: "Lun a vie 8 a 20",
    people: [{ cast: "cliente", name: "Martina" }, { cast: "integrador", name: "Diego" }] },
  { name: "Administración", desc: "Facturas, pagos y cuotas", horario: "Lun a vie 9 a 17",
    people: [{ cast: "cliente2", name: "Julián" }] },
];

const AreaCard: React.FC<{ a: Area; y: number; at: number; sel: number; dim: number; ringAt?: number }> = ({ a, y, at, sel, dim, ringAt }) => {
  const t = useT();
  const p = useIn(at, 0.6);
  const ringing = ringAt !== undefined && t > ringAt ? 0.5 + 0.5 * Math.abs(Math.sin((t - ringAt) * 5)) : 0;
  return (
    <div style={{
      position: "absolute", left: 210, top: y, width: 800, height: 250, borderRadius: 30, background: "#fff",
      border: `3px solid ${sel > 0.5 ? C.accent : C.line}`, boxShadow: sel > 0.5 ? "0 18px 44px rgba(36,86,230,.20)" : shadowCard,
      opacity: p * (1 - dim * 0.55), transform: `translateX(${(1 - p) * 60}px) scale(${1 + sel * 0.03})`, padding: "28px 34px",
    }}>
      <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 44, color: C.ink, letterSpacing: "-0.01em" }}>{a.name}</div>
      <div style={{ fontFamily: F.body, fontSize: 26, color: C.muted, marginTop: 4 }}>{a.desc}</div>
      <div style={{
        marginTop: 18, display: "inline-flex", alignItems: "center", gap: 10, background: C.surface2, borderRadius: 999,
        padding: "8px 18px", fontFamily: F.body, fontWeight: 700, fontSize: 24, color: C.ink2,
      }}>
        <Icon name="clock" size={24} color={C.ink2} />
        {a.horario}
      </div>
      <div style={{ position: "absolute", right: 30, top: 66, display: "flex", gap: 16 }}>
        {a.people.map((pp, i) => (
          <div key={pp.name} style={{ textAlign: "center" }}>
            <Cara cast={pp.cast} n={i + 1} size={100} ring={i === 0 ? ringing : 0} />
            <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 22, color: C.ink2, marginTop: 8 }}>{pp.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// 3. Áreas: el agente elige una y llama a sus personas en orden, dentro del horario.
export const Areas: React.FC = () => {
  const t = useT();
  const frame = useCurrentFrame();
  const ys = [640, 940, 1240];
  const pick = interpolate(t, [2.6, 3.6], [0, 1], { ...CLAMP, easing: EASE });
  // Paquete: baja por el tronco y entra a Ventas
  const py = interpolate(pick, [0, 0.7], [560, ys[0] + 125], CLAMP);
  const px = interpolate(pick, [0.7, 1], [130, 210], CLAMP);
  const llamando = useIn(4.3, 0.4);
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Si pide una persona" text="Elige el área y" accent="llama a su gente en orden." size={58} />
      <div style={{ position: "absolute", left: 70, top: 410, display: "flex", alignItems: "center", gap: 22, opacity: useIn(0.2, 0.5) }}>
        <AgenteLogo size={130} />
        <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 32, color: C.ink }}>Tu agente</div>
      </div>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <path d={`M 135 545 L 135 ${ys[2] + 125}`} stroke={C.line2} strokeWidth={5} strokeDasharray="10 12" strokeDashoffset={-frame * 2} />
        {ys.map((y) => <path key={y} d={`M 135 ${y + 125} L 210 ${y + 125}`} stroke={C.line2} strokeWidth={5} />)}
        <path d={`M 135 545 L 135 ${ys[0] + 125} L 210 ${ys[0] + 125}`} stroke={C.accent} strokeWidth={7} fill="none"
          strokeDasharray={900} strokeDashoffset={900 * (1 - pick)} />
      </svg>
      {t > 2.6 && t < 3.8 ? (
        <div style={{
          position: "absolute", left: px - 26, top: py - 26, width: 52, height: 52, borderRadius: 26, background: C.accent,
          display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 18px rgba(36,86,230,.35)",
        }}>
          <Icon name="phone" size={26} color="#fff" />
        </div>
      ) : null}
      {AREAS.map((a, i) => (
        <AreaCard key={a.name} a={a} y={ys[i]} at={0.7 + i * 0.3} sel={i === 0 ? pick : 0} dim={i === 0 ? 0 : pick}
          ringAt={i === 0 ? 4.2 : undefined} />
      ))}
      <div style={{
        position: "absolute", left: 210, top: 1560, display: "inline-flex", alignItems: "center", gap: 14, opacity: llamando,
        background: C.okSoft, color: C.ok, borderRadius: 999, padding: "14px 28px", fontFamily: F.body, fontWeight: 800, fontSize: 30,
      }}>
        <Icon name="phone" size={30} color={C.ok} />
        Ventas atiende ahora: llama a Lucía, después a Diego
      </div>
    </AbsoluteFill>
  );
};

// 4. Espera: música para el cliente, aviso a la persona y se conectan cuando marca 1.
export const Espera: React.FC = () => {
  const t = useT();
  const frame = useCurrentFrame();
  const musica = useIn(0.6, 0.5);
  const aviso = useIn(2.6, 0.6);
  const tecla = usePop(4.4);
  const conecta = interpolate(t, [4.9, 5.6], [0, 1], { ...CLAMP, easing: EASE });
  const pressed = t > 4.6 && t < 5.0;
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Mientras espera" text="Música para el cliente y" accent="un aviso para tu equipo." size={58} />
      {/* Cliente con música */}
      <div style={{ position: "absolute", left: 70, top: 420 }}>
        <Person {...CAST.cliente} size={330} pose="phone" mood={conecta > 0.5 ? "happy" : "neutral"} />
      </div>
      <div style={{
        position: "absolute", left: 430, top: 500, width: 560, borderRadius: 28, background: "#fff", border: `3px solid ${C.line}`,
        boxShadow: shadowCard, padding: "26px 30px", opacity: musica * (1 - conecta * 0.6),
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 22, letterSpacing: "0.08em", color: C.accent }}>EL CLIENTE ESCUCHA</div>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 42, color: C.ink, marginTop: 6 }}>Música de espera</div>
      </div>
      <Nota x={880} y={470} at={0.8} />
      <Nota x={940} y={480} at={1.5} />
      <Nota x={820} y={490} at={2.2} />
      {/* Agente que llama */}
      <div style={{ position: "absolute", left: 460, top: 860, opacity: useIn(0.3, 0.5) * (1 - conecta * 0.5) }}>
        <AgenteLogo size={160} />
      </div>
      {/* Persona del equipo con el aviso */}
      <div style={{ position: "absolute", left: 690, top: 1090 }}>
        <Person {...CAST.duena} size={330} pose="phone" mood="happy" />
      </div>
      <div style={{
        position: "absolute", left: 70, top: 1120, width: 620, borderRadius: 28, background: C.ink, color: "#fff",
        padding: "26px 30px", opacity: aviso, transform: `translateY(${(1 - aviso) * 24}px)`,
      }}>
        <div style={{ fontFamily: F.mono, fontSize: 22, letterSpacing: "0.08em", color: C.accentOnDark }}>LUCÍA ESCUCHA ANTES</div>
        <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 32, lineHeight: 1.3, marginTop: 10 }}>
          “Derivación de Ventas: presupuesto para dos splits. Marcá 1 para atender.”
        </div>
      </div>
      <div style={{
        position: "absolute", left: 300, top: 1430, width: 110, height: 110, borderRadius: 24,
        background: pressed ? C.accent : "#fff", color: pressed ? "#fff" : C.ink, border: `3px solid ${C.accent}`,
        display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.display, fontWeight: 800, fontSize: 60,
        transform: `scale(${tecla * (pressed ? 0.92 : 1)})`, boxShadow: shadowCard,
      }}>1</div>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, opacity: conecta }}>
        <path d="M 330 760 C 330 960, 860 900, 860 1100" fill="none" stroke={C.ok} strokeWidth={8} strokeLinecap="round"
          strokeDasharray="16 14" strokeDashoffset={-frame * 3} />
      </svg>
      <div style={{
        position: "absolute", left: 460, top: 1470, display: "inline-flex", alignItems: "center", gap: 12, opacity: conecta,
        background: C.okSoft, color: C.ok, borderRadius: 999, padding: "14px 28px", fontFamily: F.body, fontWeight: 800, fontSize: 32,
      }}>
        <Icon name="check" size={30} color={C.ok} />
        Conectados
      </div>
    </AbsoluteFill>
  );
};

// 5. Si nadie atiende o está fuera de horario: el agente vuelve y toma el mensaje.
export const Fallback: React.FC = () => {
  const t = useT();
  const no1 = useIn(0.7, 0.3);
  const no2 = useIn(1.3, 0.3);
  const fuera = useIn(2.0, 0.5);
  const vuelve = useIn(2.7, 0.6);
  const Fila: React.FC<{ cast: keyof typeof CAST; name: string; n: number; p: number }> = ({ cast, name, n, p }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
      <Cara cast={cast} n={n} size={92} dim={1 - p * 0.4} />
      <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 30, color: C.ink2, width: 130 }}>{name}</div>
      <div style={{
        display: "inline-flex", alignItems: "center", gap: 8, background: C.warnSoft, color: C.warn, borderRadius: 999,
        padding: "8px 18px", fontFamily: F.body, fontWeight: 800, fontSize: 24, opacity: p,
      }}>
        <Icon name="missed" size={24} color={C.warn} /> No atiende
      </div>
    </div>
  );
  return (
    <AbsoluteFill>
      <Titulo eyebrow="Si nadie atiende" text="El agente vuelve y" accent="toma el mensaje." size={60} />
      <div style={{
        position: "absolute", left: 90, top: 420, width: 900, borderRadius: 30, background: "#fff", border: `3px solid ${C.line}`,
        boxShadow: shadowCard, padding: "28px 34px", opacity: useIn(0.2, 0.5),
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 42, color: C.ink, marginBottom: 18 }}>Ventas</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Fila cast="duena" name="Lucía" n={1} p={no1} />
          <Fila cast="integrador" name="Diego" n={2} p={no2} />
        </div>
      </div>
      <div style={{
        position: "absolute", left: 90, top: 840, width: 900, borderRadius: 30, background: "#fff", border: `3px solid ${C.line}`,
        boxShadow: shadowCard, padding: "24px 34px", display: "flex", alignItems: "center", justifyContent: "space-between",
        opacity: fuera, transform: `translateY(${(1 - fuera) * 20}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ink }}>Administración</div>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8, background: C.surface2, color: C.ink2, borderRadius: 999,
          padding: "8px 18px", fontFamily: F.body, fontWeight: 800, fontSize: 24,
        }}>
          <Icon name="clock" size={24} color={C.ink2} /> Fuera de horario
        </div>
      </div>
      <div style={{ position: "absolute", left: 90, top: 1090, opacity: vuelve, transform: `scale(${0.9 + 0.1 * vuelve})` }}>
        <AgenteLogo size={150} talk={t > 2.9 && t < 5.2 ? 0.7 : 0} />
      </div>
      <div style={{
        position: "absolute", left: 270, top: 1100, width: 720, borderRadius: 30, background: C.accent, color: "#fff",
        padding: "26px 32px", fontFamily: F.body, fontWeight: 600, fontSize: 32, lineHeight: 1.3, opacity: vuelve,
        transform: `translateY(${(1 - vuelve) * 24}px)`,
      }}>
        “No pude comunicarte con Ventas en este momento. Si querés, te tomo el mensaje y te contactan más tarde.”
      </div>
    </AbsoluteFill>
  );
};

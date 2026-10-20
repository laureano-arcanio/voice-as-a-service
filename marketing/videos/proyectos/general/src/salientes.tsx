import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, Icon, Pill, useIn, usePop } from "../../../src/comun/ui";

// Campos reales de POST /api/v1/campaigns (CampaignIn, canal voice): ventana, días, concurrencia, reintentos y seguimiento
const CONFIG = [
  { k: "Contactos", v: "clientes.csv · 1.240", icon: "upload" as const },
  { k: "Agente", v: "Seguimiento" },
  { k: "Horario", v: "Lun a vie · 9 a 18 h" },
  { k: "En paralelo", v: "8 llamadas" },
  { k: "Reintentos", v: "3 intentos, cada 60 min" },
  { k: "Si no atiende", v: "WhatsApp de seguimiento", icon: "wa" as const },
];

type Result = "ok" | "retry" | "wa";
const PEOPLE: { name: string; cast: keyof typeof CAST; res: Result }[] = [
  { name: "Ana López", cast: "cliente3", res: "ok" },
  { name: "Diego Ruiz", cast: "cliente2", res: "ok" },
  { name: "Sofía Medina", cast: "cliente", res: "retry" },
  { name: "Pablo Giménez", cast: "otro", res: "ok" },
  { name: "Laura Paz", cast: "duena", res: "wa" },
  { name: "Tomás Díaz", cast: "integrador", res: "ok" },
];

const START = 3.3; // arranca la campaña
const DIAL = 1.1; // cuánto suena cada una

const status = (t: number, i: number, res: Result) => {
  const at = START + 0.25 + i * 0.32;
  if (t < at) return { label: "En cola", bg: C.surface2, fg: C.muted, dialing: false };
  if (t < at + DIAL) return { label: "Llamando…", bg: C.accentSoft, fg: C.accent, dialing: true };
  if (res === "ok") return { label: "✓ Atendió", bg: C.okSoft, fg: C.ok, dialing: false };
  if (res === "retry") return { label: "No atendió · reintenta 15:00", bg: "#fff4e5", fg: "#b25e09", dialing: false };
  return { label: "Contestador · WhatsApp enviado", bg: "#e3f6ec", fg: C.wa, dialing: false };
};

/** 5. Llamadas salientes: se programa la campaña (por panel o API) y Atentina llama, con reintentos y seguimiento. */
export const Salientes: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const card = usePop(0.15);
  const rows = CONFIG.map((_, i) => useIn(0.5 + i * 0.25, 0.3));
  const api = useIn(2.0, 0.4);
  const pressed = t > 2.6 && t < 2.75;
  const scheduled = t >= 2.75;
  const running = t >= START;
  const list = usePop(1.0);
  const mascot = usePop(0.6);
  const progress = interpolate(t, [START, 9], [0, 0.26], { ...CLAMP, easing: EASE });
  const dialing = PEOPLE.map((p, i) => status(t, i, p.res).dialing);
  const anyDialing = dialing.some(Boolean);

  const ROW_Y0 = 432;
  const ROW_H = 84;
  const LIST_X = 1130;

  return (
    <AbsoluteFill>
      <Headline eyebrow="Llamadas salientes" text="Programá campañas" accent="y Atentina llama por vos." />

      {/* La campaña */}
      <Card style={{ position: "absolute", left: 110, top: 270, width: 660, padding: "24px 30px", transform: `scale(${card})`, transformOrigin: "50% 0%" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontFamily: F.mono, fontSize: 18, color: C.accent, letterSpacing: "0.08em" }}>CAMPAÑA · VOZ</div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Seguimiento de clientes</div>
          </div>
        </div>
        <div style={{ marginTop: 10 }}>
          {CONFIG.map((c, i) => (
            <div key={c.k} style={{
              display: "grid", gridTemplateColumns: "190px 1fr", alignItems: "center", padding: "12px 0", borderBottom: `2px solid ${C.line}`,
              fontFamily: F.body, fontSize: 25, opacity: rows[i], transform: `translateX(${(1 - rows[i]) * 20}px)`,
            }}>
              <span style={{ color: C.muted }}>{c.k}</span>
              <span style={{ fontWeight: 600, color: C.ink, display: "inline-flex", alignItems: "center", gap: 10 }}>
                {c.icon ? <Icon name={c.icon} size={26} color={c.icon === "wa" ? C.wa : C.accent} /> : null}{c.v}
              </span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 20 }}>
          <div style={{ background: C.accent, color: "#fff", borderRadius: 14, padding: "12px 26px", fontFamily: F.body, fontWeight: 700, fontSize: 26, transform: `scale(${pressed ? 0.93 : 1})` }}>
            Programar
          </div>
          {scheduled ? (
            running ? (
              <Pill bg={C.okSoft} fg={C.ok} style={{ fontSize: 22, padding: "8px 16px" }}>
                <span style={{ opacity: 0.5 + 0.5 * Math.abs(Math.sin(frame / 8)) }}>●</span> En curso
              </Pill>
            ) : (
              <Pill bg={C.accentSoft} fg={C.accent} style={{ fontSize: 22, padding: "8px 16px" }}><Icon name="calendar" size={22} /> Programada · lun 9:00</Pill>
            )
          ) : null}
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 19, color: C.muted, marginTop: 16, opacity: api }}>
          o por API: <span style={{ color: C.accent }}>POST /api/v1/campaigns</span>
        </div>
      </Card>

      {/* Atentina marcando, con líneas a las llamadas en curso */}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {PEOPLE.map((_, i) => (dialing[i] ? (
          <path key={i} d={`M 1000 640 C 1060 640, ${LIST_X - 60} ${ROW_Y0 + i * ROW_H + 30}, ${LIST_X + 10} ${ROW_Y0 + i * ROW_H + 30}`}
            stroke={C.accent} strokeWidth={4} strokeDasharray="3 11" strokeDashoffset={-frame * 2} strokeLinecap="round" fill="none" />
        ) : null))}
      </svg>
      <div style={{ position: "absolute", left: 800, top: 470, transform: `scale(${mascot})` }}>
        <Mascot size={300} talk={anyDialing ? 0.4 + 0.3 * Math.abs(Math.sin(frame / 4)) : 0} />
      </div>
      <Pill bg="#fff" fg={C.ink} style={{ position: "absolute", left: 812, top: 790, fontSize: 22, border: `2px solid ${C.line}`, boxShadow: shadowCard, opacity: useIn(START, 0.3), padding: "8px 16px" }}>
        <Icon name="phone" size={22} color={C.accent} /> hasta 8 a la vez
      </Pill>

      {/* Avance de la campaña */}
      <Card style={{ position: "absolute", left: LIST_X, top: 290, width: 700, padding: "22px 26px", transform: `scale(${list})`, transformOrigin: "50% 0%" }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink }}>Avance</div>
          <div style={{ fontFamily: F.mono, fontSize: 22, color: C.accent, fontVariantNumeric: "tabular-nums" }}>{Math.round(progress * 100)} %</div>
        </div>
        <div style={{ height: 12, borderRadius: 6, background: C.surface2, marginTop: 10, overflow: "hidden" }}>
          <div style={{ width: `${progress * 100}%`, height: "100%", background: C.accent, borderRadius: 6 }} />
        </div>
        <div style={{ display: "flex", gap: 22, marginTop: 10, fontFamily: F.body, fontSize: 19, color: C.muted }}>
          <span><b style={{ color: C.ok }}>{Math.round(progress * 1240 * 0.78)}</b> atendidas</span>
          <span><b style={{ color: "#b25e09" }}>{Math.round(progress * 1240 * 0.14)}</b> a reintentar</span>
          <span><b style={{ color: C.ink2 }}>{1240 - Math.round(progress * 1240)}</b> pendientes</span>
        </div>
        <div style={{ height: ROW_H * PEOPLE.length + 8 }} />
      </Card>
      {PEOPLE.map((p, i) => {
        const s = status(t, i, p.res);
        const y = ROW_Y0 + i * ROW_H;
        return (
          <div key={p.name} style={{
            position: "absolute", left: LIST_X + 26, top: y, width: 648, height: ROW_H - 8, display: "flex", alignItems: "center", gap: 16,
            borderTop: i ? `1px solid ${C.line}` : "none", opacity: list,
          }}>
            <div style={{ width: 60, height: 60, borderRadius: 30, overflow: "hidden", background: C.accentSoft, flex: "none" }}>
              <Person {...CAST[p.cast]} size={88} mood={s.label.startsWith("✓") ? "happy" : "neutral"} style={{ marginLeft: -5, marginTop: -6 }} />
            </div>
            <div style={{ flex: 1, fontFamily: F.body, fontSize: 24, fontWeight: 600, color: C.ink }}>{p.name}</div>
            <Pill bg={s.bg} fg={s.fg} style={{ fontSize: 19, padding: "6px 14px", transform: s.dialing ? `scale(${1 + 0.03 * Math.sin(frame / 2)})` : undefined }}>
              {s.label}
            </Pill>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CAST, Mascot, Person } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { Headline, Icon, Pill, useIn, usePop } from "../../../src/comun/ui";

const NAV = ["Inicio", "Conversaciones", "Llamadas", "Agentes", "Voces", "WhatsApp", "Contactos", "Campañas", "Consumos"];

const STATS = [
  { label: "Conversaciones", value: 128, fmt: (v: number) => String(Math.round(v)) },
  { label: "Objetivo cumplido", value: 87, fmt: (v: number) => `${Math.round(v)} %` },
  { label: "Minutos", value: 412, fmt: (v: number) => String(Math.round(v)) },
  { label: "Tiempo de respuesta", value: 0.9, fmt: (v: number) => `${v.toFixed(1).replace(".", ",")} s` },
];

const LIVE = [
  { ch: "phone" as const, who: "+54 11 •••• 2231", agent: "Atención", start: 34 },
  { ch: "wa" as const, who: "Martín G.", agent: "Cobranzas", start: 71 },
  { ch: "web" as const, who: "Link para llamar", agent: "Ventas", start: 12 },
];

const ROWS = [
  { when: "10:42", agent: "Atención", who: "Carolina Pérez", ch: "Teléfono", dur: "0:42", res: "Consulta resuelta", tone: "ok" },
  { when: "10:31", agent: "Ventas", who: "Lucía R.", ch: "WhatsApp", dur: "2:10", res: "Pidió presupuesto", tone: "ok" },
  { when: "10:18", agent: "Atención", who: "+54 11 •••• 8812", ch: "Teléfono", dur: "1:05", res: "Derivada a una persona", tone: "warn" },
  { when: "10:02", agent: "Cobranzas", who: "Jorge M.", ch: "Saliente", dur: "0:58", res: "Promesa de pago", tone: "ok" },
];

const fmtDur = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/** 5. El panel: estadísticas, llamadas en vivo, historial y el detalle con transcripción y datos. */
export const Panel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const win = usePop(0.1);
  const count = interpolate(t, [0.5, 1.8], [0, 1], { ...CLAMP, easing: EASE });
  const live = useIn(1.6, 0.4);
  const table = useIn(2.0, 0.4);
  const drawer = interpolate(t, [3.0, 3.5], [0, 1], { ...CLAMP, easing: EASE });
  const msgs = [useIn(3.5, 0.3), useIn(3.8, 0.3), useIn(4.1, 0.3), useIn(4.4, 0.3)];
  const datos = useIn(4.8, 0.4);
  return (
    <AbsoluteFill>
      <Headline eyebrow="Panel" text="Visibilidad total" accent="de cada llamada." />

      <div style={{ position: "absolute", left: 120, top: 250, width: 1680, height: 790, transform: `scale(${win})`, transformOrigin: "50% 100%" }}>
        <div style={{ position: "absolute", inset: 0, background: "#fff", borderRadius: 28, border: `2px solid ${C.line}`, boxShadow: "0 24px 60px rgba(11,18,32,.14)", overflow: "hidden" }}>
          {/* barra del navegador */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 20px", background: C.surface2, borderBottom: `2px solid ${C.line}` }}>
            {["#f87171", "#fbbf24", "#34d399"].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
            <div style={{ fontFamily: F.mono, fontSize: 19, color: C.muted, marginLeft: 14 }}>app.atentina.com.ar</div>
          </div>
          <div style={{ display: "flex", height: "100%" }}>
            {/* menú */}
            <div style={{ width: 250, borderRight: `2px solid ${C.line}`, padding: "22px 16px", background: "#fbfcfe" }}>
              <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 150, marginLeft: 8, marginBottom: 20 }} />
              {NAV.map((n, i) => (
                <div key={n} style={{
                  fontFamily: F.body, fontSize: 21, fontWeight: i === 0 ? 700 : 500, color: i === 0 ? C.accent : C.ink2,
                  background: i === 0 ? C.accentSoft : "transparent", borderRadius: 10, padding: "9px 14px", marginBottom: 3,
                }}>
                  {n}
                </div>
              ))}
            </div>
            {/* contenido */}
            <div style={{ flex: 1, padding: "24px 30px", position: "relative" }}>
              <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 32, color: C.ink }}>Inicio</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginTop: 16 }}>
                {STATS.map((s) => (
                  <div key={s.label} style={{ border: `2px solid ${C.line}`, borderRadius: 16, padding: "14px 18px" }}>
                    <div style={{ fontFamily: F.body, fontSize: 18, color: C.muted }}>{s.label}</div>
                    <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ink, fontVariantNumeric: "tabular-nums" }}>{s.fmt(s.value * count)}</div>
                  </div>
                ))}
              </div>

              {/* En vivo */}
              <div style={{ marginTop: 18, border: `2px solid ${C.line}`, borderRadius: 16, padding: "14px 18px", opacity: live }}>
                <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 22, color: C.ink, display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 12, height: 12, borderRadius: 6, background: C.ok, boxShadow: `0 0 0 ${4 + 4 * Math.abs(Math.sin(frame / 8))}px rgba(27,156,91,.2)` }} />
                  En vivo · 3
                </div>
                {LIVE.map((l) => (
                  <div key={l.who} style={{ display: "grid", gridTemplateColumns: "40px 1fr 160px 90px", alignItems: "center", padding: "8px 0", fontFamily: F.body, fontSize: 20, color: C.ink2, borderTop: `1px solid ${C.line}`, marginTop: 6 }}>
                    <Icon name={l.ch} size={24} color={l.ch === "wa" ? C.wa : C.accent} />
                    <span style={{ fontWeight: 600, color: C.ink }}>{l.who}</span>
                    <span>{l.agent}</span>
                    <span style={{ fontFamily: F.mono, fontSize: 19, textAlign: "right" }}>{fmtDur(l.start + t)}</span>
                  </div>
                ))}
              </div>

              {/* Conversaciones */}
              <div style={{ marginTop: 16, opacity: table }}>
                <div style={{ display: "grid", gridTemplateColumns: "90px 130px 1fr 150px 90px 1fr", gap: 10, fontFamily: F.body, fontSize: 17, color: C.muted, padding: "0 6px 8px" }}>
                  <span>Fecha</span><span>Agente</span><span>Contacto</span><span>Origen</span><span>Duración</span><span>Resultado</span>
                </div>
                {ROWS.map((r, i) => (
                  <div key={i} style={{
                    display: "grid", gridTemplateColumns: "90px 130px 1fr 150px 90px 1fr", gap: 10, alignItems: "center", fontFamily: F.body, fontSize: 19,
                    padding: "9px 6px", borderTop: `1px solid ${C.line}`, color: C.ink2, background: i === 0 && drawer > 0 ? C.accentSoft : "transparent", borderRadius: 8,
                  }}>
                    <span style={{ fontFamily: F.mono, fontSize: 17 }}>{r.when}</span>
                    <span>{r.agent}</span>
                    <span style={{ fontWeight: 600, color: C.ink }}>{r.who}</span>
                    <span>{r.ch}</span>
                    <span style={{ fontFamily: F.mono, fontSize: 17 }}>{r.dur}</span>
                    <span>
                      <Pill bg={r.tone === "ok" ? C.okSoft : "#fff4e5"} fg={r.tone === "ok" ? C.ok : "#b25e09"} style={{ fontSize: 16, padding: "4px 12px" }}>{r.res}</Pill>
                    </span>
                  </div>
                ))}
              </div>

              {/* Detalle de la conversación */}
              <div style={{
                position: "absolute", top: 0, right: 0, bottom: 40, width: 560, background: "#fff", borderLeft: `2px solid ${C.line}`,
                boxShadow: "-20px 0 50px rgba(11,18,32,.12)", padding: "22px 26px", transform: `translateX(${(1 - drawer) * 600}px)`,
              }}>
                <div style={{ fontFamily: F.mono, fontSize: 17, color: C.accent, letterSpacing: "0.08em" }}>ATENCIÓN · TELÉFONO · 0:42</div>
                <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 30, color: C.ink, marginTop: 4 }}>Carolina Pérez</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
                  {[
                    ["user", "Hola, quería hacer una consulta."],
                    ["assistant", "¡Hola, Carolina! Ya tengo tu cuenta abierta. ¿En qué te ayudo?"],
                    ["user", "Quiero actualizar mi dirección."],
                    ["assistant", "Listo, ya quedó actualizada. ¿Algo más?"],
                  ].map(([role, text], i) => (
                    <div key={i} style={{
                      alignSelf: role === "user" ? "flex-start" : "flex-end", maxWidth: 400, opacity: msgs[i],
                      background: role === "user" ? C.surface2 : C.accent, color: role === "user" ? C.ink : "#fff",
                      borderRadius: 16, padding: "10px 16px", fontFamily: F.body, fontSize: 19, lineHeight: 1.3,
                    }}>
                      {text}
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 18, opacity: datos }}>
                  <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 21, color: C.ink, marginBottom: 6 }}>Datos</div>
                  {[["Motivo", "Actualizar sus datos"], ["Observaciones", "Prefiere que la llamen a la tarde"]].map(([k, v]) => (
                    <div key={k} style={{ display: "grid", gridTemplateColumns: "150px 1fr", padding: "7px 0", borderTop: `1px solid ${C.line}`, fontFamily: F.body, fontSize: 19 }}>
                      <span style={{ color: C.muted }}>{k}</span><span style={{ fontWeight: 600, color: C.ink }}>{v}</span>
                    </div>
                  ))}
                  <Pill bg={C.okSoft} fg={C.ok} style={{ fontSize: 19, padding: "6px 14px", marginTop: 10 }}><Icon name="check" size={20} /> Consulta resuelta</Pill>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** 6. Cierre: marca, frase de la landing y todos los personajes. */
export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const line = useIn(1.2, 0.7);
  const url = useIn(3.0, 0.6);
  const cast = useIn(3.6, 0.8);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 210, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 760 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 420, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 68, lineHeight: 1.1, color: C.ctaInk, opacity: line, transform: `translateY(${(1 - line) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Telefonía, voz e inteligencia artificial<br />
        <span style={{ color: C.accentOnDark }}>en un solo servicio.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 640, display: "flex", justifyContent: "center", alignItems: "center", gap: 30, opacity: url }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 16, padding: "16px 34px", fontFamily: F.body, fontWeight: 700, fontSize: 32 }}>Probá la demo</div>
        <div style={{ fontFamily: F.mono, fontSize: 34, color: C.ctaMuted }}>atentina.com.ar</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: -40, display: "flex", justifyContent: "center", alignItems: "flex-end", gap: 34, opacity: cast, transform: `translateY(${(1 - cast) * 120}px)` }}>
        <Person {...CAST.cliente} size={240} mood="happy" />
        <Person {...CAST.cliente2} size={240} mood="happy" blinkOffset={15} />
        <Person {...CAST.duena} size={240} mood="happy" blinkOffset={30} />
        <Mascot size={270} />
        <Person {...CAST.integrador} size={240} mood="happy" blinkOffset={60} />
        <Person {...CAST.cliente3} size={240} mood="happy" blinkOffset={75} />
      </div>
    </AbsoluteFill>
  );
};

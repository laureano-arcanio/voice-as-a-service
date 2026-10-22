import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Card, Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { AT } from "./timeline";

type Canal = "phone" | "missed" | "wa" | "web";
const colorCanal = (c: Canal) => (c === "wa" ? C.wa : c === "missed" ? C.warn : C.accent);

const ChipOscuro: React.FC<{ p: number; icon: Canal | "calendar" | "users" | "store" | "chart"; children: React.ReactNode }> = ({ p, icon, children }) => (
  <div style={{
    display: "inline-flex", alignItems: "center", gap: 12, borderRadius: 999, padding: "12px 26px", fontFamily: F.body, fontWeight: 600,
    fontSize: 28, background: "#16213a", color: C.ctaInk, border: "2px solid #23304d", transform: `scale(${p})`, opacity: Math.min(1, p * 1.5),
  }}>
    <Icon name={icon} size={28} color={C.accentOnDark} />
    {children}
  </div>
);

/** 0. Intro oscura: para quién es y la temporada. */
export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const title = useIn(0.5, 0.7);
  const t0 = 1.4;
  const chips = [usePop(t0), usePop(t0 + 0.25), usePop(t0 + 0.5), usePop(t0 + 0.75), usePop(t0 + 1.0), usePop(t0 + 1.25)];
  const items: { icon: React.ComponentProps<typeof ChipOscuro>["icon"]; t: string }[] = [
    { icon: "phone", t: "Llamadas" },
    { icon: "wa", t: "WhatsApp" },
    { icon: "web", t: "Consultar precio" },
    { icon: "calendar", t: "Instalaciones" },
    { icon: "store", t: "Service" },
    { icon: "users", t: "Cursos" },
  ];
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 360 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 290, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PARA ISAÍAS GOLDMAN SA · CÓRDOBA
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 84,
        lineHeight: 1.08, color: C.ctaInk, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        En temporada de aires,<br /><span style={{ color: C.accentOnDark }}>las consultas no paran.</span>
      </div>
      <div style={{ position: "absolute", left: 200, right: 200, top: 700, display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 18 }}>
        {items.map((x, i) => <ChipOscuro key={x.t} p={chips[i]} icon={x.icon}>{x.t}</ChipOscuro>)}
      </div>
    </AbsoluteFill>
  );
};

const FILAS: { c: Canal; texto: string; hora: string; estado: string }[] = [
  { c: "missed", texto: "Llamada perdida", hora: "10:42", estado: "Sin atender" },
  { c: "wa", texto: "¿Split 3000 frigorías instalado?", hora: "11:15", estado: "Sin responder" },
  { c: "web", texto: "Consultar precio · Split inverter", hora: "12:30", estado: "Sin responder" },
  { c: "missed", texto: "Llamada perdida", hora: "13:20", estado: "Local cerrado" },
  { c: "missed", texto: "Llamada perdida", hora: "18:47", estado: "Local cerrado" },
  { c: "wa", texto: "¿Instalan el sábado a la tarde?", hora: "21:05", estado: "Local cerrado" },
];

// Horario del local (Google Maps): lunes a viernes de 8:30 a 13 y de 14:30 a 18:30
const H0 = 8;
const H1 = 22;
const ABIERTO: [number, number][] = [[8.5, 13], [14.5, 18.5]];
const CONSULTAS = [9.1, 10.2, 11.4, 12.2, 13.3, 13.8, 15.6, 16.9, 18.9, 19.6, 20.4, 21.3];
const abierto = (h: number) => ABIERTO.some(([a, b]) => h >= a && h < b);

/** 1. El problema: un solo número, el local cerrado y la consulta que se va. */
export const Problema: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.g2;
  const izq = useIn(AT.g2 + 0.0, 0.6);
  const filas = FILAS.map((_, i) => interpolate(t, [0.4 + i * 0.3, 0.8 + i * 0.3], [0, 1], { ...CLAMP, easing: EASE }));
  const horario = useIn(AT.g2 + 2.6, 0.6);
  const puntos = CONSULTAS.map((_, i) => interpolate(t, [3.0 + i * 0.15, 3.3 + i * 0.15], [0, 1], CLAMP));
  const espera = useIn(AT.g2 + 5.0, 0.6);
  const minutos = interpolate(t, [5.4, 7.6], [0, 18], CLAMP);
  const seVa = interpolate(t, [7.8, 8.6], [0, 1], { ...CLAMP, easing: EASE });
  const nota = useIn(AT.g2 + 6.0, 0.6);
  const ancho = 740;
  const x = (h: number) => ((h - H0) / (H1 - H0)) * ancho;
  return (
    <AbsoluteFill>
      <Headline eyebrow="El problema" text="La consulta que no se contesta en minutos" accent="se va a otro lado." size={54} />

      {/* Un solo número */}
      <Card style={{ position: "absolute", left: 120, top: 250, width: 760, height: 680, padding: "30px 34px", boxSizing: "border-box", opacity: izq, transform: `translateY(${(1 - izq) * 30}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ width: 76, height: 76, borderRadius: 38, background: C.accentSoft, display: "flex", alignItems: "center", justifyContent: "center", gap: 2 }}>
            <Icon name="phone" size={32} color={C.accent} />
            <Icon name="wa" size={30} color={C.wa} />
          </div>
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 40, color: C.ink }}>Un solo número</div>
            <div style={{ fontFamily: F.body, fontSize: 23, color: C.muted }}>Teléfono y WhatsApp para ventas, instalaciones, service y cursos</div>
          </div>
        </div>
        <div style={{ marginTop: 22 }}>
          {FILAS.map((r, i) => (
            <div key={i} style={{
              display: "grid", gridTemplateColumns: "44px 1fr 74px 170px", alignItems: "center", gap: 10, padding: "21px 4px",
              borderTop: `2px solid ${C.line}`, opacity: filas[i], transform: `translateX(${(1 - filas[i]) * -30}px)`,
            }}>
              <Icon name={r.c} size={30} color={colorCanal(r.c)} />
              <span style={{ fontFamily: F.body, fontWeight: 600, fontSize: 25, color: C.ink, whiteSpace: "nowrap", overflow: "hidden" }}>{r.texto}</span>
              <span style={{ fontFamily: F.mono, fontSize: 20, color: C.muted }}>{r.hora}</span>
              <span style={{
                justifySelf: "end", background: C.warnSoft, color: C.warn, borderRadius: 999, padding: "5px 14px",
                fontFamily: F.body, fontWeight: 700, fontSize: 19, whiteSpace: "nowrap",
              }}>{r.estado}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Horario del local */}
      <Card style={{ position: "absolute", left: 960, top: 250, width: 840, height: 300, padding: "28px 34px", boxSizing: "border-box", opacity: horario, transform: `translateY(${(1 - horario) * 30}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Icon name="clock" size={34} color={C.accent} />
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Horario del local</div>
        </div>
        <div style={{ position: "relative", height: 150, marginTop: 20 }}>
          {/* barra del día */}
          <div style={{ position: "absolute", left: 0, top: 50, width: ancho, height: 40, borderRadius: 12, background: `repeating-linear-gradient(135deg, ${C.surface2} 0 10px, ${C.line} 10px 20px)` }} />
          {ABIERTO.map(([a, b]) => (
            <div key={a} style={{ position: "absolute", left: x(a), top: 50, width: x(b) - x(a), height: 40, borderRadius: 10, background: C.accent }} />
          ))}
          <div style={{ position: "absolute", left: x(13), width: x(14.5) - x(13), top: 98, textAlign: "center", fontFamily: F.mono, fontSize: 20, color: C.warn }}>cerrado</div>
          <div style={{ position: "absolute", left: x(18.5), width: x(22) - x(18.5), top: 98, textAlign: "center", fontFamily: F.mono, fontSize: 20, color: C.warn }}>cerrado</div>
          {[8, 12, 16, 20].map((h) => (
            <div key={h} style={{ position: "absolute", left: x(h) - 30, width: 60, top: 128, textAlign: "center", fontFamily: F.mono, fontSize: 17, color: C.muted }}>{h}:00</div>
          ))}
          {/* consultas que llegan */}
          {CONSULTAS.map((h, i) => {
            const fuera = !abierto(h);
            return (
              <div key={h} style={{
                position: "absolute", left: x(h) - 11, top: 10 + (1 - puntos[i]) * -20, width: 22, height: 22, borderRadius: 11,
                background: fuera ? C.warn : C.ok, border: "3px solid #fff", boxShadow: shadowCard, opacity: puntos[i],
              }} />
            );
          })}
        </div>
      </Card>

      {/* La consulta que espera y se va */}
      <Card style={{ position: "absolute", left: 960, top: 590, width: 840, height: 340, padding: "28px 34px", boxSizing: "border-box", opacity: espera, transform: `translateY(${(1 - espera) * 30}px)`, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 34, color: C.ink }}>Esperando respuesta</div>
          <div style={{ fontFamily: F.mono, fontSize: 44, color: minutos > 5 ? C.warn : C.ink, fontVariantNumeric: "tabular-nums" }}>
            {Math.floor(minutos)} min
          </div>
        </div>
        <div style={{
          marginTop: 30, display: "inline-flex", alignItems: "center", gap: 14, background: C.surface2, borderRadius: 20, padding: "16px 24px",
          fontFamily: F.body, fontWeight: 600, fontSize: 27, color: C.ink, opacity: 1 - seVa, transform: `translateX(${seVa * 500}px)`,
        }}>
          <Icon name="wa" size={30} color={C.wa} />
          ¿Tienen un split de 3000 frigorías instalado?
        </div>
        <div style={{ position: "absolute", left: 34, bottom: 34, display: "flex", alignItems: "center", gap: 14, opacity: seVa, fontFamily: F.body, fontWeight: 700, fontSize: 30, color: C.warn }}>
          <svg width={60} height={22}><path d="M2 11 H54 M44 3 L56 11 L44 19" stroke={C.warn} strokeWidth={3.5} fill="none" strokeLinecap="round" /></svg>
          Le escribió a otro negocio
        </div>
      </Card>

      <div style={{ position: "absolute", left: 120, right: 120, top: 968, textAlign: "center", fontFamily: F.mono, fontSize: 22, color: C.muted, opacity: nota }}>
        Lo dicen sus propios clientes: las quejas son de atención, no de producto.
      </div>
    </AbsoluteFill>
  );
};

/** 4. Cierre: el piloto desde noviembre. */
export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const line = useIn(0.5, 0.7);
  const canales = [usePop(1.3), usePop(1.5), usePop(1.7), usePop(1.9)];
  const contacto = useIn(2.4, 0.6);
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 210, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo-blanco.svg")} style={{ width: 520 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 390, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accentOnDark, opacity: useIn(0.3, 0.5) }}>
        PROPUESTA PARA ISAÍAS GOLDMAN SA · PILOTO DE 30 DÍAS DESDE NOVIEMBRE
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 460, textAlign: "center", fontFamily: F.display, fontWeight: 800,
        fontSize: 72, lineHeight: 1.1, color: C.ctaInk, opacity: line, transform: `translateY(${(1 - line) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Que cada consulta tenga respuesta,<br /><span style={{ color: C.accentOnDark }}>y que ustedes las vean todas.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 710, display: "flex", justifyContent: "center", gap: 18 }}>
        <ChipOscuro p={canales[0]} icon="phone">0800 / 0810</ChipOscuro>
        <ChipOscuro p={canales[1]} icon="wa">WhatsApp</ChipOscuro>
        <ChipOscuro p={canales[2]} icon="web">Chat en la web</ChipOscuro>
        <ChipOscuro p={canales[3]} icon="chart">Panel</ChipOscuro>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 850, display: "flex", justifyContent: "center", alignItems: "center", gap: 30, opacity: contacto }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 16, padding: "16px 34px", fontFamily: F.body, fontWeight: 700, fontSize: 32 }}>
          Coordinemos el piloto
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 32, color: C.ctaMuted }}>atentina.com.ar · 0800-220-1233</div>
      </div>
    </AbsoluteFill>
  );
};

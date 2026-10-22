import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn } from "../../../src/comun/ui";
import { NAR, NAR_SOFT, Pie } from "./escenas";
import { AT } from "./timeline";

// Momentos de a4 (s desde que arranca la voz), por las pausas de la toma
const M = { numero: 1.0, productos: 2.75, horas: 6.35, temporada: 9.35 };

const Tarjeta: React.FC<{ x: number; y: number; p: number; titulo: string; texto: string; children: React.ReactNode }> = ({
  x, y, p, titulo, texto, children,
}) => (
  <div style={{
    position: "absolute", left: x, top: y, width: 825, height: 340, boxSizing: "border-box", padding: "28px 36px",
    background: "#fff", border: `2px solid ${C.line}`, borderLeft: `10px solid ${NAR}`, borderRadius: 24, boxShadow: shadowCard,
    opacity: p, transform: `translateY(${(1 - p) * 30}px)`,
  }}>
    <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 42, lineHeight: 1.1, color: C.ink, letterSpacing: "-0.01em" }}>{titulo}</div>
    <div style={{ height: 150, marginTop: 14, position: "relative" }}>{children}</div>
    <div style={{ fontFamily: F.body, fontSize: 23, lineHeight: 1.3, color: C.ink2 }}>{texto}</div>
  </div>
);

const TEMAS = ["Ventas", "Instaladores", "Empresas", "Turnos", "Service", "Reclamos", "Cursos"];
const DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
// Horario publicado en Google Maps: lu a vie 8:30–13 y 14:30–18:30; sáb 8:30–13; dom cerrado
const ABIERTO: [number, number][][] = [
  ...Array(5).fill([[8.5, 13], [14.5, 18.5]]),
  [[8.5, 13]],
  [],
];
const MESES = ["Sep", "Oct", "Nov", "Dic", "Ene", "Feb", "Mar"];

/** 2. Lo que observamos: cuatro hechos que cualquier cliente ve hoy. */
export const Observamos: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a4;
  const p = [useIn(AT.a4 + M.numero, 0.6), useIn(AT.a4 + M.productos, 0.6), useIn(AT.a4 + M.horas, 0.6), useIn(AT.a4 + M.temporada, 0.6)];
  const temas = TEMAS.map((_, i) => interpolate(t, [M.numero + 0.3 + i * 0.12, M.numero + 0.6 + i * 0.12], [0, 1], CLAMP));
  const productos = Math.round(interpolate(t, [M.productos + 0.2, M.productos + 1.6], [0, 266], { ...CLAMP, easing: EASE }));
  const semana = interpolate(t, [M.horas + 0.2, M.horas + 1.4], [0, 1], CLAMP);
  const horas = Math.round(121 * semana);
  const meses = interpolate(t, [M.temporada + 0.3, M.temporada + 1.0], [0, 1], CLAMP);
  const W = 500;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que observamos" text="Lo que ve cualquier cliente:" accent="cómo se llega a ustedes." size={60} />

      <Tarjeta x={120} y={250} p={p[0]} titulo="Un solo número para todo"
        texto="El mismo teléfono y WhatsApp en el sitio, Google, Facebook y Linktree.">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, width: 430 }}>
          {TEMAS.map((x, i) => (
            <div key={x} style={{
              borderRadius: 999, padding: "6px 14px", background: C.surface2, fontFamily: F.body, fontWeight: 600, fontSize: 20, color: C.ink2,
              opacity: temas[i], transform: `translateX(${(1 - temas[i]) * -20}px)`,
            }}>{x}</div>
          ))}
        </div>
        <svg width={80} height={40} style={{ position: "absolute", left: 445, top: 50 }}>
          <path d="M4 20 H66 M54 8 L70 20 L54 32" stroke={NAR} strokeWidth={4} fill="none" strokeLinecap="round" opacity={temas[6]} />
        </svg>
        <div style={{
          position: "absolute", left: 535, top: 34, display: "flex", alignItems: "center", gap: 8, borderRadius: 16, padding: "14px 16px",
          background: NAR_SOFT, border: `2px solid ${NAR}`, opacity: temas[6],
        }}>
          <Icon name="phone" size={26} color={NAR} />
          <Icon name="wa" size={26} color={C.wa} />
          <span style={{ fontFamily: F.mono, fontSize: 20, color: C.ink, whiteSpace: "nowrap" }}>351 386 2886</span>
        </div>
      </Tarjeta>

      <Tarjeta x={975} y={250} p={p[1]} titulo="266 productos, ninguno con precio"
        texto="Cada ficha termina en “Consultar precio”: un formulario por email.">
        <div style={{ display: "flex", gap: 16 }}>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{ width: 150, height: 140, borderRadius: 14, border: `2px solid ${C.line}`, background: C.bg2, padding: 12, boxSizing: "border-box" }}>
              <div style={{ height: 52, borderRadius: 8, background: C.surface2, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: 90, height: 24, borderRadius: 6, border: `2px solid ${C.line2}`, background: "#fff" }} />
              </div>
              <div style={{ height: 9, width: 100, borderRadius: 5, background: C.line, marginTop: 10 }} />
              <div style={{ marginTop: 12, borderRadius: 8, background: C.ink2, color: "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 15, textAlign: "center", padding: "6px 0" }}>
                Consultar precio
              </div>
            </div>
          ))}
          <div style={{ marginLeft: 14, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 64, color: NAR, fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{productos}</div>
            <div style={{ fontFamily: F.mono, fontSize: 18, color: C.muted }}>sin precio</div>
          </div>
        </div>
      </Tarjeta>

      <Tarjeta x={120} y={622} p={p[2]} titulo="121 de las 168 horas, cerrado"
        texto="Lu a vie de 8:30 a 13 y de 14:30 a 18:30; sábados hasta las 13.">
        <div style={{ position: "relative" }}>
          {DIAS.map((d, i) => (
            <div key={d} style={{ display: "flex", alignItems: "center", gap: 10, height: 19, marginBottom: 1 }}>
              <span style={{ width: 30, fontFamily: F.mono, fontSize: 14, color: C.muted }}>{d}</span>
              <div style={{ position: "relative", width: W, height: 14, borderRadius: 4, background: C.surface2, overflow: "hidden" }}>
                <div style={{ position: "absolute", left: 0, top: 0, height: 14, width: W * semana, background: "#f6c9ad" }} />
                {ABIERTO[i].map(([a, b]) => (
                  <div key={a} style={{ position: "absolute", left: (a / 24) * W, width: ((b - a) / 24) * W, top: 0, height: 14, background: C.ok }} />
                ))}
              </div>
            </div>
          ))}
          <div style={{ position: "absolute", left: 560, top: 8, whiteSpace: "nowrap" }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 64, color: NAR, fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{horas} h</div>
            <div style={{ fontFamily: F.mono, fontSize: 17, color: C.muted, marginTop: 8 }}>cerrado por semana</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: F.mono, fontSize: 17, color: C.muted, marginTop: 8 }}>
              <span style={{ width: 14, height: 14, borderRadius: 3, background: C.ok }} />abierto
              <span style={{ width: 14, height: 14, borderRadius: 3, background: "#f6c9ad", marginLeft: 10 }} />cerrado
            </div>
          </div>
        </div>
      </Tarjeta>

      <Tarjeta x={975} y={622} p={p[3]} titulo="La temporada arranca en noviembre"
        texto="De noviembre a febrero se juntan consultas, instalaciones y reclamos.">
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", height: 130 }}>
          {MESES.map((m, i) => {
            const pico = i >= 2 && i <= 5;
            const h = 96;
            return (
              <div key={m} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <div style={{ width: 82, height: h, borderRadius: 10, background: pico ? (meses > 0.1 ? NAR : C.line) : C.surface2, transform: `scale(${pico ? 1 + 0.08 * meses : 1})`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {pico ? <Icon name={i === 2 ? "clock" : "users"} size={28} color="#fff" /> : null}
                </div>
                <span style={{ fontFamily: F.mono, fontSize: 18, color: pico ? C.ink : C.muted }}>{m}</span>
              </div>
            );
          })}
        </div>
      </Tarjeta>

      <Pie seccion="2 / 4" fuente="Fuentes: su sitio, Google Maps y redes, leídos el 21-oct-2026." />
    </AbsoluteFill>
  );
};

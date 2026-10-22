import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Headline, useIn } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// Las dos reseñas del PDF baicenter-propuesta v1 (página 2), textuales y sin nombres.
// `foco`: cuándo la nombra la locución (s desde que arranca a5): "una respuesta rápida" 4,05 · "un próximo paso" 5,5
const CITAS = [
  { titulo: "La primera respuesta", cita: "5 días esperando respuesta", nota: "Por WhatsApp, con el contacto “en línea”.", cuando: "Google Maps · hace unos 6 meses", at: 2.6, foco: 4.05 },
  { titulo: "Después de la visita", cita: "tomaron el número y me despacharon", nota: "Al día siguiente le llegaron los precios, pero nadie le habló de la forma de pago.", cuando: "Google Maps · hace alrededor de un año", at: 2.8, foco: 5.5 },
];

const Estrellas: React.FC<{ p: number; valor: number }> = ({ p, valor }) => (
  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
    {[0, 1, 2, 3, 4].map((i) => {
      const lleno = Math.max(0, Math.min(1, p * valor - i));
      return (
        <svg key={i} viewBox="0 0 24 24" width={36} height={36}>
          <defs>
            <linearGradient id={`bst${i}`}>
              <stop offset={lleno} stopColor="#f5b301" />
              <stop offset={lleno} stopColor={C.line} />
            </linearGradient>
          </defs>
          <path d="M12 2.5l2.9 6 6.6.8-4.9 4.5 1.3 6.5L12 17l-5.9 3.3 1.3-6.5L2.5 9.3l6.6-.8z" fill={`url(#bst${i})`} />
        </svg>
      );
    })}
  </div>
);

/** 3. Lo que piden sus clientes: lo bueno primero, dos reseñas y lo que tienen en común. */
export const Clientes: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a5;
  const bueno = useIn(AT.a5 + 0.1, 0.6);
  const est = interpolate(t, [0.4, 1.4], [0, 1], CLAMP);
  const destacaBueno = interpolate(t, [0.2, 0.5, 2.3, 2.6], [0, 1, 1, 0], CLAMP);
  const ins = CITAS.map((c) => useIn(AT.a5 + c.at, 0.6));
  const comun = useIn(AT.a5 + 5.9, 0.6);
  const activa = (i: number) => {
    const ini = CITAS[i].foco;
    const fin = CITAS[i + 1]?.foco ?? 99;
    return interpolate(t, [ini - 0.15, ini + 0.15, fin - 0.15, fin + 0.15], [0, 1, 1, 0], CLAMP);
  };
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que piden sus clientes" text="No piden otro auto:" accent="una respuesta rápida y un próximo paso." size={58} />

      {/* Lo positivo primero */}
      <div style={{
        position: "absolute", left: 120, top: 262, width: 540, height: 680, boxSizing: "border-box", padding: "30px 34px",
        background: C.okSoft, border: `2px solid ${destacaBueno > 0.5 ? C.ok : "#bfe6cf"}`, borderRadius: 24,
        opacity: bueno, transform: `translateY(${(1 - bueno) * 30}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ok }}>Lo que también se ve</div>
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 18 }}>
          <span style={{ fontFamily: F.display, fontWeight: 800, fontSize: 84, color: C.ink, lineHeight: 1 }}>{(4.0 * est).toFixed(1).replace(".", ",")}</span>
          <Estrellas p={est} valor={4.0} />
        </div>
        <div style={{ fontFamily: F.body, fontSize: 27, lineHeight: 1.35, color: C.ink, marginTop: 14 }}>
          La mayoría de las reseñas en Google son buenas.
        </div>
        <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.35, color: C.ink2, marginTop: 18 }}>
          Compradores de X35, X55 y BJ30 cuentan su experiencia.
        </div>
        <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.35, color: C.ink2, marginTop: 18 }}>
          Y Edgardo contesta en persona, también las difíciles:{" "}
          <i style={{ color: C.ink }}>“sirve para mejorar nuestros procesos de atención”.</i>
        </div>
      </div>

      {CITAS.map((c, i) => {
        const on = activa(i);
        const dim = t >= CITAS[0].foco - 0.15 && on < 0.5 ? 0.6 : 1;
        return (
          <div key={c.titulo} style={{
            position: "absolute", left: i === 0 ? 690 : 1260, top: 262, width: 540, height: 400, boxSizing: "border-box", padding: "28px 32px",
            background: C.bg2, borderRadius: 24, border: `2px solid ${on > 0.5 ? C.accent : C.line}`,
            boxShadow: on > 0.5 ? "0 0 0 6px rgba(36,86,230,.14), " + shadowCard : "none",
            opacity: ins[i] * dim, transform: `translateY(${(1 - ins[i]) * 30}px) scale(${1 + 0.025 * on})`,
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>{c.titulo}</div>
            <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 40, lineHeight: 1.15, color: C.ink, marginTop: 16, fontStyle: "italic" }}>“{c.cita}”</div>
            <div style={{ fontFamily: F.body, fontSize: 25, lineHeight: 1.35, color: C.ink2, marginTop: 14 }}>{c.nota}</div>
            <div style={{ position: "absolute", left: 32, bottom: 24, fontFamily: F.mono, fontSize: 16, letterSpacing: "0.04em", color: C.muted, textTransform: "uppercase" }}>{c.cuando}</div>
          </div>
        );
      })}

      <div style={{
        position: "absolute", left: 690, top: 690, width: 1110, height: 252, boxSizing: "border-box", padding: "28px 34px",
        background: C.accentSoft, border: "2px solid #c9d7ff", borderRadius: 24, opacity: comun, transform: `translateY(${(1 - comun) * 30}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.accent2 }}>Lo que tienen en común</div>
        <div style={{ fontFamily: F.body, fontSize: 28, lineHeight: 1.38, color: C.ink, marginTop: 12 }}>
          Clientes con ganas de comprar que esperaban el paso siguiente: una respuesta, una llamada, una propuesta de pago.{" "}
          <b style={{ color: C.accent2 }}>Bien atendido en el primer minuto, es una venta.</b>
        </div>
      </div>

      <Pie seccion="3 / 4" fuente="Reseñas públicas de Google Maps (4,0 con 77), textuales y sin nombres, leídas el 20-oct-2026." />
    </AbsoluteFill>
  );
};

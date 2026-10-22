import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, F, shadowCard } from "../../../src/comun/theme";
import { Headline, useIn } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// Reseñas públicas de Google Maps, textuales y sin nombres (PDF goldman-propuesta v1, página 2)
// `at`: cuándo aparece; `foco`: cuándo la nombra la locución (s desde que arranca a5)
const CITAS = [
  { titulo: "El llamado", cita: "siempre te dicen que te vuelven a llamar, y no lo hacen", cuando: "Google Maps · hace un año", at: 1.7, foco: 3.0 },
  { titulo: "El presupuesto", cita: "La debilidad es la atencion telefónica y via mail para pedir presupuestos, tardan mucho tiempo.", cuando: "Google Maps · 4 estrellas · hace 3 años", at: 1.85, foco: 3.75 },
  { titulo: "El precio", cita: "me pasaron un precio por Whatsapp y al llegar a la sucursal me dieron otro", cuando: "Google Maps · hace un año", at: 2.0, foco: 99 },
  { titulo: "La visita técnica", cita: "esperé toda la tarde que venga el técnico que nunca llegó ni tampoco avisaron", cuando: "Google Maps · hace un año", at: 2.15, foco: 5.2 },
  { titulo: "El mostrador", cita: "Se tarda muchísimo para atender.", cuando: "Google Maps · hace 10 meses", at: 2.3, foco: 99 },
];
const FOCOS = [3.0, 3.75, 5.2]; // v3, a5 a 1x

/** 3. Lo que dicen sus clientes: lo bueno primero, y lo que se repite. */
export const Clientes: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a5;
  const bueno = useIn(AT.a5 + 0.1, 0.6);
  const ins = CITAS.map((c) => useIn(AT.a5 + c.at, 0.6));
  // La cita nombrada se resalta hasta que se nombra la siguiente
  const activa = (foco: number) => {
    if (!FOCOS.includes(foco)) return 0;
    const sig = FOCOS.find((x) => x > foco) ?? 99;
    return interpolate(t, [foco - 0.15, foco + 0.15, sig - 0.15, sig + 0.15], [0, 1, 1, 0], CLAMP);
  };
  const algunaActiva = t >= FOCOS[0] - 0.15;
  const pos = [
    { x: 690, y: 262 }, { x: 1260, y: 262 },
    { x: 120, y: 612 }, { x: 690, y: 612 }, { x: 1260, y: 612 },
  ];
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que dicen sus clientes" text="Lo que se repite:" accent="poder comunicarse." />

      {/* Lo que también dicen: primero, lo bueno */}
      <div style={{
        position: "absolute", left: 120, top: 262, width: 540, height: 320, boxSizing: "border-box", padding: "26px 30px",
        background: C.okSoft, border: "2px solid #bfe6cf", borderRadius: 24, opacity: bueno, transform: `translateY(${(1 - bueno) * 30}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ok }}>Lo que también dicen</div>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 38, lineHeight: 1.15, color: C.ink, marginTop: 14, fontStyle: "italic" }}>
          “Excelente atención en el local”
        </div>
        <div style={{ fontFamily: F.body, fontSize: 23, lineHeight: 1.35, color: C.ink2, marginTop: 14 }}>
          Y ustedes contestan las reseñas, también las malas.
        </div>
      </div>

      {CITAS.map((c, i) => {
        const on = activa(c.foco);
        const dim = algunaActiva && on < 0.5 ? 0.55 : 1;
        return (
          <div key={c.titulo} style={{
            position: "absolute", left: pos[i].x, top: pos[i].y, width: 540, height: 320, boxSizing: "border-box", padding: "26px 30px",
            background: C.bg2, borderRadius: 24, border: `2px solid ${on > 0.5 ? C.accent : C.line}`,
            boxShadow: on > 0.5 ? "0 0 0 6px rgba(36,86,230,.14), " + shadowCard : "none",
            opacity: ins[i] * dim, transform: `translateY(${(1 - ins[i]) * 30}px) scale(${1 + 0.025 * on})`,
          }}>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 32, color: C.ink }}>{c.titulo}</div>
            <div style={{ fontFamily: F.body, fontSize: 27, lineHeight: 1.35, color: C.ink, marginTop: 14, fontStyle: "italic" }}>“{c.cita}”</div>
            <div style={{ position: "absolute", left: 30, bottom: 24, fontFamily: F.mono, fontSize: 16, letterSpacing: "0.04em", color: C.muted, textTransform: "uppercase" }}>{c.cuando}</div>
          </div>
        );
      })}

      <Pie seccion="3 / 4" fuente="Reseñas públicas de Google Maps, textuales y sin nombres, leídas el 21-oct-2026." />
    </AbsoluteFill>
  );
};

import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import envs from "../../../public/proyectos/sqlamoblamientos-analisis/vo/envolventes.json";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, EASE, F, shadowCard } from "../../../src/comun/theme";
import { Headline, Icon, useIn, usePop } from "../../../src/comun/ui";
import { Pie } from "./escenas";
import { AT } from "./timeline";

// Lo que más se elogia (PDF, página 2): los asesores nombrados en reseñas recientes de Google Maps.
// Momentos de a5 (s desde que arranca la voz): "Sus clientes elogian a sus asesores," 0–2,2 · "por su nombre." 2,36 ·
// "El asesor de guardia no los reemplaza:" 3,4–5,48 · "les pasa cada consulta lista." 5,77–7,4
// v6 (paula): "por su nombre." 2,0 · "El asesor de guardia no los reemplaza:" 3,0 · "les pasa cada consulta lista." 5,05–6,28
const MA = { nombre: 2.0, guardia: 3.0, reemplaza: 4.0, pasa: 5.05 };
const ASESORES = [
  { n: "Martín", d: "Casa central" },
  { n: "Fernando", d: "Casa central" },
  { n: "Micaela", d: "Villa Carlos Paz" },
  { n: "Arq. Inés", d: "Río Cuarto" },
];

/** 3. Lo que valoran sus clientes: los asesores por su nombre; el asesor de guardia les pasa la consulta lista. */
export const Clientes: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - AT.a5;
  const v = (s: number) => AT.a5 + s;
  const nombres = ASESORES.map((_, i) => usePop(v(0.4 + i * 0.25)));
  const foco = interpolate(t, [MA.nombre, MA.nombre + 0.4], [0, 1], CLAMP);
  const cita = useIn(v(1.6), 0.6);
  const derecha = useIn(v(MA.guardia - 0.2), 0.6);
  const logo = usePop(v(MA.guardia));
  const asesor = usePop(v(MA.reemplaza));
  const viaje = interpolate(t, [MA.pasa + 0.1, MA.pasa + 1.0], [0, 1], { ...CLAMP, easing: EASE });
  const viajeO = interpolate(t, [MA.pasa, MA.pasa + 0.1, MA.pasa + 1.0, MA.pasa + 1.3], [0, 1, 1, 0], CLAMP);
  const llego = interpolate(t, [MA.pasa + 0.9, MA.pasa + 1.2], [0, 1], CLAMP);
  const env = envs.a5;
  const i = frame - Math.round(v(0) * fps);
  const talk = i >= 0 && i < env.length ? env[i] * 0.5 : 0;
  return (
    <AbsoluteFill>
      <Headline eyebrow="Lo que valoran sus clientes" text="Lo que más se elogia:" accent="sus asesores, por su nombre." size={60} />

      {ASESORES.map((a, n) => (
        <div key={a.n} style={{
          position: "absolute", left: 120 + (n % 2) * 440, top: 262 + Math.floor(n / 2) * 150, width: 420, height: 130, boxSizing: "border-box",
          padding: "0 26px", display: "flex", alignItems: "center", gap: 18, borderRadius: 22, background: foco > 0.5 ? C.okSoft : "#fff",
          border: `2px solid ${foco > 0.5 ? C.ok : C.line}`, boxShadow: shadowCard, transform: `scale(${nombres[n]})`, opacity: Math.min(1, nombres[n] * 1.5),
        }}>
          <div style={{ width: 64, height: 64, flex: "none", borderRadius: 32, background: C.okSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="users" size={34} color={C.ok} />
          </div>
          <div>
            <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 38, color: C.ink, lineHeight: 1.05 }}>{a.n}</div>
            <div style={{ fontFamily: F.mono, fontSize: 17, color: C.muted, marginTop: 6 }}>{a.d}</div>
          </div>
        </div>
      ))}

      <div style={{
        position: "absolute", left: 120, top: 576, width: 860, height: 366, boxSizing: "border-box", padding: "30px 36px",
        background: C.bg2, borderLeft: `8px solid ${C.ok}`, borderRadius: 24, opacity: cita, transform: `translateY(${(1 - cita) * 24}px)`,
      }}>
        <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 40, lineHeight: 1.2, color: C.ink, fontStyle: "italic" }}>
          “la atención de Martin antes, durante y pos a la venta. Los plazos de entrega fueron los pactados”
        </div>
        <div style={{ position: "absolute", left: 36, bottom: 26, fontFamily: F.mono, fontSize: 17, letterSpacing: "0.04em", color: C.muted }}>
          GOOGLE MAPS · CASA CENTRAL · HACE 4 MESES
        </div>
      </div>

      {/* El asesor de guardia no los reemplaza: les pasa la consulta lista */}
      <div style={{
        position: "absolute", left: 1040, top: 262, width: 760, height: 680, boxSizing: "border-box", borderRadius: 24, background: C.accentSoft,
        border: "2px solid #c9d7ff", opacity: derecha, transform: `translateY(${(1 - derecha) * 24}px)`,
      }}>
        <div style={{ position: "absolute", left: 70, top: 70, display: "flex", flexDirection: "column", alignItems: "center", transform: `scale(${logo})` }}>
          <AgenteLogo size={170} talk={talk} style={{ filter: "drop-shadow(0 14px 26px rgba(36,86,230,.22))" }} />
          <div style={{ marginTop: 12, background: C.ink, color: "#fff", borderRadius: 999, padding: "8px 18px", fontFamily: F.mono, fontSize: 18, whiteSpace: "nowrap" }}>
            Asesor de guardia
          </div>
        </div>
        <svg width={760} height={680} style={{ position: "absolute", inset: 0 }}>
          <path d="M260 155 C 360 155, 380 155, 470 155" stroke={C.accent} strokeWidth={4} strokeDasharray="10 10" fill="none" opacity={asesor * 0.7} />
        </svg>
        <div style={{
          position: "absolute", left: 270 + 140 * viaje, top: 129, width: 92, height: 52, borderRadius: 26, background: C.ink, opacity: viajeO,
          display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.mono, fontSize: 18, color: "#fff",
        }}>ficha</div>
        <div style={{
          position: "absolute", left: 480, top: 80, width: 220, height: 150, boxSizing: "border-box", borderRadius: 22,
          background: "#fff", border: `${llego > 0.5 ? 3 : 2}px solid ${llego > 0.5 ? C.ok : C.line}`, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 8, transform: `scale(${asesor * (1 + 0.05 * llego)})`, opacity: Math.min(1, asesor * 1.5),
          boxShadow: shadowCard,
        }}>
          <Icon name="users" size={44} color={C.ok} />
          <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: 28, color: C.ink }}>Su asesor</div>
        </div>
        <div style={{ position: "absolute", left: 50, right: 50, top: 340, fontFamily: F.display, fontWeight: 800, fontSize: 40, lineHeight: 1.15, color: C.ink, opacity: asesor }}>
          No los reemplaza: <span style={{ color: C.accent }}>les pasa cada consulta lista.</span>
        </div>
        <div style={{ position: "absolute", left: 50, right: 50, top: 480, fontFamily: F.body, fontSize: 28, lineHeight: 1.38, color: C.ink2, opacity: llego }}>
          La venta es personal y así tiene que seguir. El asesor de guardia califica la consulta y cuida que nadie quede esperando.
        </div>
      </div>

      <Pie seccion="3 / 4" fuente="Reseñas públicas de Google Maps (casa central, Carlos Paz y Río Cuarto), leídas el 22-oct-2026." />
    </AbsoluteFill>
  );
};

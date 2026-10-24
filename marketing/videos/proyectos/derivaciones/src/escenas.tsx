import React from "react";
import { AbsoluteFill } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, F } from "../../../src/comun/theme";
import { useIn, usePop } from "../../../src/comun/ui";
import { Pantalla, Titulo } from "./pantalla";

// Intro, pasos con capturas reales del panel (390 px) y cierre.

const Oscuro: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ background: C.ink }}>
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.1 }}>
      <defs>
        <pattern id="dots-dark" width={36} height={36} patternUnits="userSpaceOnUse">
          <circle cx={2} cy={2} r={1.6} fill={C.ctaMuted} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#dots-dark)" />
    </svg>
    {children}
  </AbsoluteFill>
);

// 1. Apertura.
export const Intro: React.FC = () => {
  const p = useIn(0.15, 0.8);
  const s = usePop(0.3);
  const q = useIn(1.2, 0.7);
  return (
    <Oscuro>
      <div style={{ position: "absolute", left: 84, right: 84, top: 470, opacity: p }}>
        <div style={{ transform: `scale(${s})`, transformOrigin: "left center", width: 210 }}>
          <AgenteLogo size={190} />
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 26, letterSpacing: "0.12em", color: C.accentOnDark, marginTop: 58 }}>
          TRANSFERENCIA DE LLAMADAS
        </div>
        <div style={{
          fontFamily: F.display, fontWeight: 800, fontSize: 80, lineHeight: 1.03, letterSpacing: "-0.02em", color: "#fff", marginTop: 18,
        }}>
          Tu agente atiende y, cuando hace falta, <span style={{ color: C.accentOnDark }}>te pasa la llamada.</span>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 36, color: C.ctaMuted, marginTop: 34, opacity: q }}>
          Equipo, áreas y el agente, paso a paso.
        </div>
      </div>
    </Oscuro>
  );
};

// 6. Paso 1: Equipo > Agregar persona.
export const Equipo: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 1 · Equipo" text="Sumá a cada persona" accent="con su teléfono." />
    <Pantalla
      pasos={[
        { img: "01-menu", from: 0 },
        { img: "02-equipo", from: 1.5 },
        { img: "03-persona", from: 2.7 },
        { img: "04-equipo-con-lucia", from: 4.7 },
      ]}
      toques={[
        { x: 120, y: 432, at: 1.2 },
        { x: 270, y: 218, at: 2.4 },
        { x: 279, y: 628, at: 4.4 },
      ]}
    />
  </AbsoluteFill>
);

// 7. Paso 2: Crear área (nombre, qué atiende, personas en orden).
export const Area: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 2 · Áreas" text="Cada área, con sus personas" accent="en orden." />
    <Pantalla
      pasos={[
        { img: "04-equipo-con-lucia", from: 0 },
        { img: "05-area-top", from: 1.2 },
      ]}
      toques={[{ x: 290, y: 569, at: 0.9 }]}
      zoom={{ from: 3.6, to: 4.4, scale: 1.12, x: 195, y: 520 }}
    />
  </AbsoluteFill>
);

// 8. Paso 3: horario y mensajes.
export const Horario: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 3 · Horario y mensajes" text="Su horario, y los mensajes" accent="ya escritos." />
    <Pantalla
      pasos={[
        { img: "07-area-horario", from: 0 },
        { img: "09-area-mensajes", from: 2.8 },
      ]}
      toques={[{ x: 59, y: 176, at: 0.9 }]}
    />
  </AbsoluteFill>
);

// 9. Paso 4: en el agente, Derivación a personas.
export const Agente: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 4 · El agente" text="Marcá a qué áreas" accent="puede pasar la llamada." />
    <Pantalla
      pasos={[
        { img: "12-agente-derivacion", from: 0 },
        { img: "12b-agente-ventas", from: 4.4 },
      ]}
      toques={[
        { x: 60, y: 304, at: 1.6 },
        { x: 60, y: 517, at: 2.3 },
        { x: 60, y: 768, at: 3.0 },
        { x: 195, y: 280, at: 5.0 },
      ]}
    />
  </AbsoluteFill>
);

// 10. Paso 5: música de espera y guardar.
export const Guardar: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 5 · Guardar" text="Música de espera prendida y" accent="una versión nueva." />
    <Pantalla
      pasos={[
        { img: "13-agente-musica", from: 0 },
        { img: "14-guardado", from: 2.6 },
      ]}
      toques={[{ x: 56, y: 404, at: 1.0 }]}
    />
  </AbsoluteFill>
);

// 11. Resultado: la conversación con el tramo de la persona del equipo.
export const Resultado: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="El resultado" text="En la conversación ves" accent="el tramo con tu equipo." />
    <Pantalla
      pasos={[{ img: "16-llamada-tramo", from: 0 }]}
      zoom={{ from: 1.6, to: 2.6, scale: 1.1, x: 195, y: 640 }}
    />
  </AbsoluteFill>
);

// 12. Cierre.
export const Cierre: React.FC = () => {
  const p = useIn(0.15, 0.8);
  const q = useIn(1.4, 0.7);
  return (
    <Oscuro>
      <div style={{ position: "absolute", left: 84, right: 84, top: 560, opacity: p }}>
        <AgenteLogo size={170} />
        <div style={{
          fontFamily: F.display, fontWeight: 800, fontSize: 80, lineHeight: 1.03, letterSpacing: "-0.02em", color: "#fff", marginTop: 56,
        }}>
          Tu agente resuelve lo que puede. <span style={{ color: C.accentOnDark }}>Lo demás, tu equipo.</span>
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 34, color: C.ctaMuted, marginTop: 50, opacity: q }}>
          app.atentina.com.ar → Equipo
        </div>
      </div>
    </Oscuro>
  );
};

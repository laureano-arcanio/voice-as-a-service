import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { AgenteLogo } from "../../../src/comun/characters";
import { C, CLAMP, F } from "../../../src/comun/theme";
import { useIn, usePop } from "../../../src/comun/ui";
import { Pantalla, Titulo, useT } from "./pantalla";

// Intro, pasos con capturas reales del panel (390 px, plan Free) y cierre. Los toques salen de
// capturas/taps.json (coordenadas CSS de cada captura).

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

/** Aviso sobre la pantalla (en CSS px de la captura): aparece en `at`. */
const Aviso: React.FC<{ at: number; top: number; children: React.ReactNode }> = ({ at, top, children }) => {
  const t = useT();
  const p = interpolate(t, [at, at + 0.35], [0, 1], CLAMP);
  const K = 640 / 390;
  return (
    <div style={{
      position: "absolute", left: 24 * K, right: 24 * K, top: top * K, opacity: p,
      transform: `translateY(${(1 - p) * 24}px)`,
    }}>
      {children}
    </div>
  );
};

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
          PLAN FREE · PRIMEROS PASOS
        </div>
        <div style={{
          fontFamily: F.display, fontWeight: 800, fontSize: 80, lineHeight: 1.03, letterSpacing: "-0.02em", color: "#fff", marginTop: 18,
        }}>
          Tu agente, creado y probado <span style={{ color: C.accentOnDark }}>desde el celular.</span>
        </div>
        <div style={{ fontFamily: F.body, fontSize: 36, color: C.ctaMuted, marginTop: 34, opacity: q }}>
          Crear, probar y compartir, paso a paso.
        </div>
      </div>
    </Oscuro>
  );
};

// 2. Inicio > menú > Agentes > Mis agentes > Nuevo agente.
export const Agentes: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 1 · Agentes" text="Abrí el menú y creá" accent="un agente nuevo." />
    <Pantalla
      pasos={[
        { img: "01-inicio", from: 0 },
        { img: "02-menu", from: 1.15 },
        { img: "03-menu-agentes", from: 2.05 },
        { img: "04-agentes", from: 2.95 },
      ]}
      toques={[
        { x: 30, y: 30, at: 0.9 },
        { x: 120, y: 176, at: 1.8 },
        { x: 150, y: 219, at: 2.7 },
        { x: 91, y: 178, at: 4.1 },
      ]}
    />
  </AbsoluteFill>
);

// 3. Modal Nuevo agente: nombre, Asistente básico y Crear agente.
export const Nombre: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 2 · Nombre" text="Un nombre y" accent="el asistente básico." />
    <Pantalla
      pasos={[
        { img: "05-modal", from: 0 },
        { img: "06-modal-nombre", from: 1.5 },
        { img: "07-def", from: 4.75 },
      ]}
      toques={[{ x: 290, y: 702, at: 4.5 }]}
      zoom={{ from: 0.9, to: 1.6, scale: 1.12, x: 195, y: 280, back: 3.4 }}
    />
  </AbsoluteFill>
);

// 4. Definición: el rol y la base de conocimiento con los precios; guardar.
export const Definicion: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 3 · Lo que sabe" text="El menú, los precios" accent="y los horarios." />
    <Pantalla
      pasos={[
        { img: "08-rol-antes", from: 0 },
        { img: "09-rol", from: 1.0 },
        { img: "10-kb-antes", from: 2.0 },
        { img: "11-kb-1", from: 2.5 },
        { img: "11-kb-2", from: 3.0 },
        { img: "11-kb-3", from: 3.4 },
        { img: "11-kb-4", from: 3.8 },
        { img: "12-guardar", from: 5.2 },
        { img: "13-guardado", from: 6.1 },
      ]}
      toques={[
        { x: 195, y: 422, at: 0.8 },
        { x: 217, y: 152, at: 5.85 },
      ]}
      zoom={{ from: 2.2, to: 2.8, scale: 1.12, x: 195, y: 160, back: 4.5 }}
    />
  </AbsoluteFill>
);

// 5. Probar: pestaña Probar, Probar agente y la llamada de prueba en el navegador.
export const Probar: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 4 · Probar" text="Hablale desde" accent="el navegador." sub="No marca ningún teléfono ni gasta minutos." />
    <Pantalla
      pasos={[
        { img: "14-probar-tab", from: 0 },
        { img: "15-probar-voz", from: 1.5 },
        { img: "16-llamada-prueba", from: 3.2 },
        { img: "17-llamada-prueba-chat", from: 5.4 },
      ]}
      toques={[{ x: 112, y: 302, at: 2.9 }]}
    />
  </AbsoluteFill>
);

// 6. Link para llamar: crear, copiar y compartir.
export const Link: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Paso 5 · Compartir" text="Copiá el link" accent="y compartilo." sub="Usa los minutos del plan: 20 por mes en Free." />
    <Pantalla
      pasos={[
        { img: "18-link-vacio", from: 0 },
        { img: "19-link-creado", from: 1.45 },
        { img: "20-link-copiado", from: 2.75 },
      ]}
      toques={[
        { x: 96, y: 567, at: 1.2 },
        { x: 235, y: 586, at: 2.5 },
      ]}
    >
      <Aviso at={2.8} top={520}>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <div style={{
            background: C.ink, color: "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 30, padding: "14px 30px",
            borderRadius: 999, boxShadow: "0 12px 30px rgba(11,18,32,.25)",
          }}>
            Link copiado
          </div>
        </div>
      </Aviso>
      <Aviso at={3.7} top={630}>
        <div style={{
          background: "#fff", borderRadius: 26, padding: "22px 26px", boxShadow: "0 18px 50px rgba(11,18,32,.28)",
          border: `1px solid ${C.line}`, fontFamily: F.body, fontSize: 28, color: C.ink, lineHeight: 1.3,
        }}>
          <div style={{ fontFamily: F.mono, fontSize: 20, color: C.muted, letterSpacing: "0.06em", marginBottom: 8 }}>MENSAJE</div>
          Consultá el menú y los precios de El Fogón, llamando acá:
          <div style={{ fontFamily: F.mono, fontSize: 25, color: C.accent, marginTop: 8 }}>llamar.atentina.com.ar/yFVEqe9lijm1</div>
        </div>
      </Aviso>
    </Pantalla>
  </AbsoluteFill>
);

// 7. La página que abre quien recibe el link: Llamar y la llamada en curso.
export const Quien: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Quien recibe el link" text="Toca Llamar y" accent="habla con tu agente." sub="Sin instalar nada ni registrarse." />
    <Pantalla
      pasos={[
        { img: "21-llamar", from: 0 },
        { img: "22-llamar-en-llamada", from: 1.9 },
      ]}
      toques={[{ x: 195, y: 683, at: 1.6 }]}
    />
  </AbsoluteFill>
);

// 8. Conversaciones: la lista y el detalle con la transcripción.
export const Conversaciones: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Conversaciones" text="Cada llamada," accent="con su transcripción." />
    <Pantalla
      pasos={[
        { img: "23-conversaciones", from: 0 },
        { img: "24-detalle", from: 1.9 },
        { img: "25-detalle-chat", from: 3.6 },
      ]}
      toques={[{ x: 110, y: 574, at: 1.6 }]}
    />
  </AbsoluteFill>
);

// 9. Lo que no incluye el Free: candados, Equipo con el aviso y los planes.
export const Planes: React.FC = () => (
  <AbsoluteFill>
    <Titulo eyebrow="Planes pagos" text="Equipo, número propio y WhatsApp:" accent="Mostrador, Sucursal y Central." size={56} />
    <Pantalla
      pasos={[
        { img: "26-menu-plan", from: 0 },
        { img: "27-equipo", from: 2.4 },
        { img: "28-planes", from: 5.2 },
      ]}
      toques={[
        { x: 120, y: 334, at: 2.1 },
        { x: 120, y: 279, at: 4.9 },
      ]}
      zoom={{ from: 2.9, to: 3.5, scale: 1.1, x: 195, y: 300, back: 4.3 }}
    />
  </AbsoluteFill>
);

// 10. Cierre.
export const Cierre: React.FC = () => {
  const p = useIn(0.15, 0.8);
  const q = useIn(1.2, 0.7);
  return (
    <Oscuro>
      <div style={{ position: "absolute", left: 84, right: 84, top: 600, opacity: p }}>
        <AgenteLogo size={170} />
        <div style={{
          fontFamily: F.display, fontWeight: 800, fontSize: 84, lineHeight: 1.03, letterSpacing: "-0.02em", color: "#fff", marginTop: 56,
        }}>
          Creá tu primer agente. <span style={{ color: C.accentOnDark }}>Gratis.</span>
        </div>
        <div style={{ fontFamily: F.mono, fontSize: 34, color: C.ctaMuted, marginTop: 50, opacity: q }}>
          app.atentina.com.ar
        </div>
      </div>
    </Oscuro>
  );
};

import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, F } from "../../../src/comun/theme";
import { Headline, useIn, usePop } from "../../../src/comun/ui";

const DIR = "proyectos/prueba-imagenes";

/** Foto a sangre con Ken Burns lento; velo blanco arriba para que el título se lea siempre. */
const Foto: React.FC<{ img: string; eyebrow: string; text: string; accent: string }> = ({ img, eyebrow, text, accent }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const z = interpolate(frame, [0, durationInFrames], [1, 1.08], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <Img src={staticFile(`${DIR}/img/${img}`)}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: `scale(${z})` }} />
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 300,
        background: "linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(255,255,255,0.6) 55%, rgba(255,255,255,0) 100%)" }} />
      <Headline eyebrow={eyebrow} text={text} accent={accent} />
    </AbsoluteFill>
  );
};

/** Placa de marca generada (fondo blanco con grilla de puntos); el centro de la imagen queda libre. */
export const Marca: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const z = interpolate(frame, [0, durationInFrames], [1, 1.04], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <Img src={staticFile(`${DIR}/img/03-marca.png`)}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", transform: `scale(${z})` }} />
      <Headline eyebrow="TODO REGISTRADO" text="La conversación, los datos" accent="y el resultado." />
    </AbsoluteFill>
  );
};

// ---------- 0. intro: blanco, logo y frase ----------

export const Intro: React.FC = () => {
  const logo = usePop(0.1);
  const rótulo = useIn(0.25, 0.5);
  const title = useIn(0.4, 0.7);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 320 }} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 330, textAlign: "center", fontFamily: F.mono, fontSize: 26, letterSpacing: "0.1em", color: C.accent, opacity: rótulo }}>
        AGENTES CON IA
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 390, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 84,
        lineHeight: 1.08, color: C.ink, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Atendé cada llamada,<br /><span style={{ color: C.accent }}>a cualquier hora.</span>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 1 y 2. fotos de día (Qwen-Image-2.1, estilo foto) ----------

export const Cafe: React.FC = () => (
  <Foto img="01-cafe.png" eyebrow="TU NEGOCIO" text="El teléfono suena" accent="mientras atendés." />
);

export const Equipo: React.FC = () => (
  <Foto img="02-oficina.png" eyebrow="TU EQUIPO" text="Lo importante le llega" accent="a tu equipo." />
);

// ---------- 4. cierre: blanco, logo y contacto ----------

export const Cierre: React.FC = () => {
  const logo = usePop(0.15);
  const title = useIn(0.4, 0.7);
  const url = useIn(1.2, 0.6);
  const tel = useIn(1.7, 0.6);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 200, display: "flex", justifyContent: "center", transform: `scale(${logo})` }}>
        <Img src={staticFile("marca/atentina-logo.svg")} style={{ width: 420 }} />
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: F.display, fontWeight: 800, fontSize: 86,
        lineHeight: 1.08, color: C.ink, opacity: title, transform: `translateY(${(1 - title) * 24}px)`, letterSpacing: "-0.015em",
      }}>
        Agentes con IA que atienden<br /><span style={{ color: C.accent }}>a tus clientes.</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 640, display: "flex", justifyContent: "center", opacity: url, transform: `translateY(${(1 - url) * 14}px)` }}>
        <div style={{ background: C.accent, color: "#fff", borderRadius: 999, padding: "16px 40px", fontFamily: F.mono, fontSize: 40 }}>atentina.com.ar</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 750, textAlign: "center", fontFamily: F.body, fontWeight: 600, fontSize: 30, color: C.muted, opacity: tel }}>
        o llamá al 0800-220-1233 y hablá con nuestro agente
      </div>
    </AbsoluteFill>
  );
};

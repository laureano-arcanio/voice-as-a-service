import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP } from "../../../src/comun/theme";
import { Marca, Momento1, Momento2, Momento3, Momento4, Momento5 } from "./momentos";
import { CRUCE, MOMENTOS, T } from "./timeline";

/**
 * Landing, sección de la plataforma: el panel para configurar un agente en cinco momentos (voz, herramientas,
 * derivación, prueba y reportes). Vertical 4:5 (1080 x 1350), sin audio, en loop: empieza y termina en blanco.
 */

const COMPONENTES = { m1: Momento1, m2: Momento2, m3: Momento3, m4: Momento4, m5: Momento5 };

const Entra: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, f(CRUCE)], [0, 1], CLAMP);
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

export const LandingPanelVideo: React.FC = () => (
  <AbsoluteFill style={{ background: C.bg }}>
    <Sequence from={0} durationInFrames={f(T.m1 + CRUCE)}>
      <Marca lineas={["Todo tu agente,"]} acento="en un solo panel." de={T.logoIn} hasta={99} />
    </Sequence>
    {MOMENTOS.map((m) => {
      const Comp = COMPONENTES[m.id];
      return (
        <Sequence key={m.id} from={f(m.de)} durationInFrames={f(m.a - m.de + CRUCE)}>
          <Entra><Comp /></Entra>
        </Sequence>
      );
    })}
    <Sequence from={f(T.cierre)} durationInFrames={f(T.fin - T.cierre)}>
      <Entra>
        <Marca lineas={["Agentes con IA", "que atienden"]} acento="a tus clientes." de={0.15} hasta={T.cierreOut - T.cierre} />
      </Entra>
    </Sequence>
  </AbsoluteFill>
);

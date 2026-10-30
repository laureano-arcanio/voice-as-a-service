import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP } from "../../../src/comun/theme";
import { Momento1, Momento2, Momento3, Momento4, Momento5 } from "./momentos";
import { BLANCO, CRUCE, MOMENTOS, T } from "./timeline";

/**
 * Landing, sección de la plataforma: el panel para configurar un agente en cinco momentos (voz, herramientas,
 * derivación, prueba y reportes). Vertical 4:5 (1080 x 1350), sin audio ni texto, en loop: arranca y termina en
 * blanco con un fundido corto.
 */

const COMPONENTES = { m1: Momento1, m2: Momento2, m3: Momento3, m4: Momento4, m5: Momento5 };

const Entra: React.FC<{ children: React.ReactNode; fundido: boolean }> = ({ children, fundido }) => {
  const frame = useCurrentFrame();
  const o = fundido ? interpolate(frame, [0, f(CRUCE)], [0, 1], CLAMP) : 1;
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

export const LandingPanelVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const fin = f(T.fin);
  const blanco = Math.max(
    interpolate(frame, [0, f(BLANCO)], [1, 0], CLAMP),
    interpolate(frame, [fin - 1 - f(BLANCO), fin - 1], [0, 1], CLAMP),
  );
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {MOMENTOS.map((m, i) => {
        const Comp = COMPONENTES[m.id];
        const largo = m.a - m.de + (i < MOMENTOS.length - 1 ? CRUCE : 0);
        return (
          <Sequence key={m.id} from={f(m.de)} durationInFrames={f(largo)}>
            <Entra fundido={i > 0}><Comp /></Entra>
          </Sequence>
        );
      })}
      <AbsoluteFill style={{ background: C.bg, opacity: blanco }} />
    </AbsoluteFill>
  );
};

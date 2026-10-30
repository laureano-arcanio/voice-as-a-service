import React from "react";
import { AbsoluteFill } from "remotion";
import { Montaje } from "../../../src/comun/montaje";
import { Cierre, Desarrolladores, Intro, Plataforma, TodoEnUno } from "./escenas";
import { Subtitulos } from "./piezas";
import { DUR, INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Video de la home de la landing (~47 s): la plataforma alrededor del agente, todo en uno y desarrolladores. */
export const LandingPlataformaVideo: React.FC = () => (
  <AbsoluteFill>
    <Montaje
      dir="proyectos/landing-plataforma"
      escenas={SCENES}
      componentes={{ intro: Intro, plataforma: Plataforma, todo: TodoEnUno, desarrolladores: Desarrolladores, cierre: Cierre }}
      voces={VOICES}
      duraciones={DUR}
      intro="intro"
      introFade={INTRO_FADE}
    />
    <Subtitulos />
  </AbsoluteFill>
);

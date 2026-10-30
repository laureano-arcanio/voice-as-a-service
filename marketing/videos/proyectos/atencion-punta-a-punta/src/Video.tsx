import React from "react";
import { AbsoluteFill } from "remotion";
import { Montaje } from "../../../src/comun/montaje";
import { Checklist, Cierre, Diagrama, Intro } from "./escenas";
import { Subtitulos } from "./piezas";
import { DUR, INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Publicitario de 60 s: la atención de punta a punta (cliente, agente, sistema y equipo) y lo que se configura. */
export const AtencionPuntaAPuntaVideo: React.FC = () => (
  <AbsoluteFill>
    <Montaje
      dir="proyectos/atencion-punta-a-punta"
      escenas={SCENES}
      componentes={{ intro: Intro, diagrama: Diagrama, checklist: Checklist, cierre: Cierre }}
      voces={VOICES}
      duraciones={DUR}
      intro="intro"
      introFade={INTRO_FADE}
    />
    <Subtitulos />
  </AbsoluteFill>
);

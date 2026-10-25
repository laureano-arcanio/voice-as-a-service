import React from "react";
import { AbsoluteFill } from "remotion";
import { Montaje } from "../../../src/comun/montaje";
import { Herramientas, Intro, Reparto, Turno } from "./escenas1";
import { Cierre, Configurar, Ejemplo, Errores, Latencia } from "./escenas2";
import { Subtitulos } from "./piezas";
import { DUR, INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Tu propio agente (custom LLM): el agente del cliente en su endpoint, con la voz y el teléfono de Atentina. */
export const TuPropioAgenteVideo: React.FC = () => (
  <AbsoluteFill>
    <Montaje
      dir="proyectos/tu-propio-agente"
      escenas={SCENES}
      componentes={{
        intro: Intro, reparto: Reparto, turno: Turno, herramientas: Herramientas, ejemplo: Ejemplo,
        configurar: Configurar, latencia: Latencia, errores: Errores, cierre: Cierre,
      }}
      voces={VOICES}
      duraciones={DUR}
      intro="intro"
      introFade={INTRO_FADE}
    />
    <Subtitulos />
  </AbsoluteFill>
);

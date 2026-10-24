import React from "react";
import dur from "../../../public/proyectos/derivaciones/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Areas, Ciclo, Espera, Fallback } from "./diagramas";
import { Agente, Area, Cierre, Equipo, Guardar, Horario, Intro, Resultado } from "./escenas";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Tutorial vertical: cómo funciona la derivación de llamadas a personas y cómo se configura. */
export const DerivacionesVideo: React.FC = () => (
  <Montaje
    dir="proyectos/derivaciones"
    escenas={SCENES}
    componentes={{
      intro: Intro,
      ciclo: Ciclo,
      areas: Areas,
      espera: Espera,
      fallback: Fallback,
      equipo: Equipo,
      area: Area,
      horario: Horario,
      agente: Agente,
      guardar: Guardar,
      resultado: Resultado,
      cierre: Cierre,
    }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

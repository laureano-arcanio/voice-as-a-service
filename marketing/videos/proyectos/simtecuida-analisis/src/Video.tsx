import React from "react";
import dur from "../../../public/proyectos/simtecuida-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Diagrama, Recorrido } from "./diagrama";
import { Cierre, Intro, Oportunidades, Presupuesto } from "./escenas";
import { Ficha, Panel } from "./ficha";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** SIM Te Cuida, todo en blanco: lo que vimos, las oportunidades, el diagrama, el recorrido, la ficha, el panel y el presupuesto. */
export const SimtecuidaAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/simtecuida-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, oportunidades: Oportunidades, diagrama: Diagrama, recorrido: Recorrido, ficha: Ficha, panel: Panel, presupuesto: Presupuesto, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

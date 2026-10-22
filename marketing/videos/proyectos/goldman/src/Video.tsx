import React from "react";
import dur from "../../../public/proyectos/goldman/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Cierre, Intro, Problema } from "./escenas";
import { Propuesta } from "./propuesta";
import { Panel } from "./panel";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Propuesta para Isaías Goldman SA: el problema en temporada, los tres canales, el panel y el piloto. */
export const GoldmanVideo: React.FC = () => (
  <Montaje
    dir="proyectos/goldman"
    escenas={SCENES}
    componentes={{ intro: Intro, problema: Problema, propuesta: Propuesta, panel: Panel, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

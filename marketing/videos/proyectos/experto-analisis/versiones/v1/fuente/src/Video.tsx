import React from "react";
import dur from "../../../public/proyectos/experto-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Bien, Cierre, Cita, Intro } from "./escenas";
import { Mejorar } from "./mejorar";
import { Panel, Propuesta } from "./propuesta";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Experto Construcción Inteligente con el formato del PDF: lo que hacen bien, dónde mejorar, la propuesta y el panel. */
export const ExpertoAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/experto-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, bien: Bien, cita: Cita, mejorar: Mejorar, propuesta: Propuesta, panel: Panel, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

import React from "react";
import dur from "../../../public/proyectos/goldman-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Bien, Cierre, Cita, Intro } from "./escenas";
import { Observamos } from "./observamos";
import { Clientes } from "./clientes";
import { Propuesta } from "./propuesta";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Isaías Goldman SA con el formato del PDF: lo que hacen bien, lo que observamos, sus clientes y la propuesta. */
export const GoldmanAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/goldman-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, bien: Bien, cita: Cita, observamos: Observamos, clientes: Clientes, propuesta: Propuesta, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

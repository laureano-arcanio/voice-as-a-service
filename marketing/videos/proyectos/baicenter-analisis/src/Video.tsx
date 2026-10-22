import React from "react";
import dur from "../../../public/proyectos/baicenter-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Bien, Cierre, Cita, Intro } from "./escenas";
import { Areas } from "./areas";
import { Clientes } from "./clientes";
import { Panel, Propuesta } from "./propuesta";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** BAIC Center / Grupo Signature con el formato del PDF: lo que hacen bien, áreas a mejorar, sus clientes, la propuesta y el panel. */
export const BaicenterAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/baicenter-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, bien: Bien, cita: Cita, areas: Areas, clientes: Clientes, propuesta: Propuesta, panel: Panel, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

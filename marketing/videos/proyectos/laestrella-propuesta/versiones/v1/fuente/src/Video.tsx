import React from "react";
import dur from "../../../public/proyectos/laestrella-propuesta/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Cierre, Datos, Etapa1, Etapa2, Funciona, Intro, Pasos, Propuesta } from "./escenas";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Empresa La Estrella: la propuesta del PDF v2 en video, todo en blanco, con paula y gonzalo en partes iguales. */
export const LaestrellaPropuestaVideo: React.FC = () => (
  <Montaje
    dir="proyectos/laestrella-propuesta"
    escenas={SCENES}
    componentes={{ intro: Intro, propuesta: Propuesta, datos: Datos, etapa1: Etapa1, etapa2: Etapa2, funciona: Funciona, pasos: Pasos, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

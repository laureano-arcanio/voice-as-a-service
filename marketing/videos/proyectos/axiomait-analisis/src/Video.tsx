import React from "react";
import dur from "../../../public/proyectos/axiomait-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Bien, Cierre, Intro, Lineas, Marcha } from "./escenas";
import { Llamador, Producto, Voces } from "./tecnica";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Axioma IT con el formato de su PDF: lo que hacen, dónde encaja la voz, el producto, el llamador del CRM, voces. */
export const AxiomaitAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/axiomait-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, bien: Bien, lineas: Lineas, producto: Producto, llamador: Llamador, voces: Voces, marcha: Marcha, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

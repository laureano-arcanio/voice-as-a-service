import React from "react";
import dur from "../../../public/proyectos/zennonbi-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Bien, Cierre, Intro, Lineas, Marcha } from "./escenas";
import { Alianza, Integracion } from "./alianza";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Zennon BI con el formato de su PDF: lo que hacen, dónde encaja la voz, la integración, la alianza y la marcha. */
export const ZennonbiAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/zennonbi-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, bien: Bien, lineas: Lineas, integracion: Integracion, alianza: Alianza, marcha: Marcha, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

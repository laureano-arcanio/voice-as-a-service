import React from "react";
import dur from "../../../public/proyectos/yoizen/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Agentes, Arquitectura, Intro } from "./escenas1";
import { Inferencia, Llamadas } from "./escenas2";
import { Cierre, Datos } from "./escenas3";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Video técnico para integradores: cómo Yoizen suma voz a sus agentes con las APIs de Atentina. */
export const YoizenVideo: React.FC = () => (
  <Montaje
    dir="proyectos/yoizen"
    escenas={SCENES}
    componentes={{ intro: Intro, arquitectura: Arquitectura, agentes: Agentes, llamadas: Llamadas, inferencia: Inferencia, datos: Datos, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

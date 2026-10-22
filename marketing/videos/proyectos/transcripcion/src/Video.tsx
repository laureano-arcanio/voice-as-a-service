import React from "react";
import dur from "../../../public/proyectos/transcripcion/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Cierre, Intro } from "./marca";
import { Panel } from "./panel";
import { Api, Integracion } from "./api";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Transcripción y síntesis de voz para call centers: panel, API e integración. */
export const TranscripcionVideo: React.FC = () => (
  <Montaje
    dir="proyectos/transcripcion"
    escenas={SCENES}
    componentes={{ intro: Intro, panel: Panel, api: Api, integracion: Integracion, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

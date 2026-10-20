import React from "react";
import dur from "../../../public/proyectos/general/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Api } from "./api";
import { Cierre, Panel } from "./panel";
import { Salientes } from "./salientes";
import { Atentina, Problema } from "./scenes1";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";
import { Viaje } from "./viaje";

/** Video general de Atentina: problema, solución, viaje de la voz, API, salientes, panel y cierre. */
export const GeneralVideo: React.FC = () => (
  <Montaje
    dir="proyectos/general"
    escenas={SCENES}
    componentes={{ intro: Cierre, problema: Problema, atentina: Atentina, viaje: Viaje, api: Api, salientes: Salientes, panel: Panel, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

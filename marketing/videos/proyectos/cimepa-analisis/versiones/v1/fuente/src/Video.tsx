import React from "react";
import dur from "../../../public/proyectos/cimepa-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Cierre, Intro, Pedido } from "./escenas";
import { Empleado, Entra, LlamaIA } from "./llamadas";
import { Agente, Registro } from "./registro";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** CIMEPA con el formato de su PDF: lo que nos pidieron, los tres flujos de llamada, el registro y su agente. */
export const CimepaAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/cimepa-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, pedido: Pedido, entra: Entra, empleado: Empleado, ia: LlamaIA, registro: Registro, agente: Agente, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

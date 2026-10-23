import React from "react";
import dur from "../../../public/proyectos/primeros-pasos/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Cierre, Definicion, Enlace, Guardar, Intro, Llamada, Nombre, Probar } from "./escenas";
import { Agentes } from "./escenas";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Tutorial vertical: crear un agente básico y probarlo con una llamada desde el navegador. */
export const PrimerosPasosVideo: React.FC = () => (
  <Montaje
    dir="proyectos/primeros-pasos"
    escenas={SCENES}
    componentes={{
      intro: Intro,
      agentes: Agentes,
      nombre: Nombre,
      definicion: Definicion,
      guardar: Guardar,
      probar: Probar,
      enlace: Enlace,
      llamada: Llamada,
      cierre: Cierre,
    }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

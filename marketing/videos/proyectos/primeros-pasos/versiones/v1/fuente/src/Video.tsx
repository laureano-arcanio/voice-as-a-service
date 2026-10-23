import React from "react";
import dur from "../../../public/proyectos/primeros-pasos/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Agentes, Apertura, Cierre, Conocimiento, Conversaciones, Guardar, Intro, Llamada, Nuevo, Probar, Voz } from "./escenas";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Primeros pasos (vertical): crear un agente con el asistente básico y probarlo con una llamada desde el navegador. */
export const PrimerosPasosVideo: React.FC = () => (
  <Montaje
    dir="proyectos/primeros-pasos"
    escenas={SCENES}
    componentes={{
      intro: Intro, agentes: Agentes, nuevo: Nuevo, voz: Voz, apertura: Apertura, conocimiento: Conocimiento, guardar: Guardar,
      probar: Probar, llamada: Llamada, conversaciones: Conversaciones, cierre: Cierre,
    }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

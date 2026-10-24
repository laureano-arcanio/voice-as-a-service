import React from "react";
import dur from "../../../public/proyectos/tutorial-agente-free-mobile/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Agentes, Cierre, Conversaciones, Definicion, Intro, Link, Nombre, Planes, Probar, Quien } from "./escenas";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Tutorial vertical para el plan Free: crear un agente, probarlo, compartir el link y ver la transcripción. */
export const TutorialAgenteFreeMobileVideo: React.FC = () => (
  <Montaje
    dir="proyectos/tutorial-agente-free-mobile"
    escenas={SCENES}
    componentes={{
      intro: Intro,
      agentes: Agentes,
      nombre: Nombre,
      definicion: Definicion,
      probar: Probar,
      link: Link,
      quien: Quien,
      conversaciones: Conversaciones,
      planes: Planes,
      cierre: Cierre,
    }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

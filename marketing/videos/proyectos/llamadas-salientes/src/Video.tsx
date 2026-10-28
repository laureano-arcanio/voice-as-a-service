import React from "react";
import { AbsoluteFill } from "remotion";
import { Montaje } from "../../../src/comun/montaje";
import { App, Cierre, Contactos, Equipo, Intro, Numero, Panel } from "./escenas";
import { Subtitulos } from "./piezas";
import { DUR, INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Tutorial para YouTube: configurar el número, cargar equipo y contactos y llamar desde el panel y la aplicación Teléfono. */
export const LlamadasSalientesVideo: React.FC = () => (
  <AbsoluteFill>
    <Montaje
      dir="proyectos/llamadas-salientes"
      escenas={SCENES}
      componentes={{ intro: Intro, numero: Numero, equipo: Equipo, contactos: Contactos, panel: Panel, app: App, cierre: Cierre }}
      voces={VOICES}
      duraciones={DUR}
      intro="intro"
      introFade={INTRO_FADE}
    />
    <Subtitulos />
  </AbsoluteFill>
);

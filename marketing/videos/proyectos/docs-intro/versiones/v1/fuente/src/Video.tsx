import React from "react";
import { AbsoluteFill } from "remotion";
import { Montaje } from "../../../src/comun/montaje";
import { Api, Cierre, Formas, Intro, Mcp } from "./escenas";
import { Subtitulos } from "./piezas";
import { DUR, INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Introducción de la documentación: las tres formas de usar Atentina (panel, MCP y API) y dónde está cada una. */
export const DocsIntroVideo: React.FC = () => (
  <AbsoluteFill>
    <Montaje
      dir="proyectos/docs-intro"
      escenas={SCENES}
      componentes={{ intro: Intro, formas: Formas, mcp: Mcp, api: Api, cierre: Cierre }}
      voces={VOICES}
      duraciones={DUR}
      intro="intro"
      introFade={INTRO_FADE}
    />
    <Subtitulos />
  </AbsoluteFill>
);

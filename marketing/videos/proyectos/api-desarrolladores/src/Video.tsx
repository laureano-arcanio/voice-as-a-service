import React from "react";
import { AbsoluteFill } from "remotion";
import { Montaje } from "../../../src/comun/montaje";
import { Auth, Capacidades, Intro } from "./escenas1";
import { Agente, Llamada, Llm, Tts } from "./escenas2";
import { Cierre, Resultado, Webhook } from "./escenas3";
import { Subtitulos } from "./piezas";
import { DUR, INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Video técnico para desarrolladores: cómo integrar la API de Atentina, con pedidos y respuestas reales. */
export const ApiDesarrolladoresVideo: React.FC = () => (
  <AbsoluteFill>
    <Montaje
      dir="proyectos/api-desarrolladores"
      escenas={SCENES}
      componentes={{ intro: Intro, capacidades: Capacidades, auth: Auth, llm: Llm, tts: Tts, agente: Agente, llamada: Llamada,
        resultado: Resultado, webhook: Webhook, cierre: Cierre }}
      voces={VOICES}
      duraciones={DUR}
      intro="intro"
      introFade={INTRO_FADE}
    />
    <Subtitulos />
  </AbsoluteFill>
);

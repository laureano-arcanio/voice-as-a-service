import React from "react";
import { AbsoluteFill } from "remotion";
import { Montaje } from "../../../src/comun/montaje";
import { ESCENAS, Subtitulos } from "./escenas";
import { DUR, SCENES, VOICES } from "./timeline";

/** Presentación para Yoizen (Tu propio agente) con audio: las 12 diapositivas, paula y gonzalo alternados. */
export const YoizenTuPropioAgenteVideo: React.FC = () => (
  <AbsoluteFill>
    <Montaje dir="proyectos/yoizen-tu-propio-agente" escenas={SCENES} componentes={ESCENAS} voces={VOICES} duraciones={DUR} />
    <Subtitulos />
  </AbsoluteFill>
);

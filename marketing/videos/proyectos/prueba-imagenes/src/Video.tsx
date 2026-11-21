import React from "react";
import { Montaje } from "../../../src/comun/montaje";
import { Cafe, Cierre, Equipo, Intro, Marca } from "./escenas";
import { SCENES } from "./timeline";

/** Prueba de punta a punta del pipeline de imágenes: API local (Qwen-Image-2.1) → make video-imagen → escenas. */
export const PruebaImagenesVideo: React.FC = () => (
  <Montaje
    dir="proyectos/prueba-imagenes"
    escenas={SCENES}
    componentes={{ intro: Intro, cafe: Cafe, equipo: Equipo, marca: Marca, cierre: Cierre }}
    voces={[]}
    duraciones={{}}
    intro="intro"
    musicVolume={0.75}
  />
);

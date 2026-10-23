import React from "react";
import dur from "../../../public/proyectos/sqlamoblamientos-analisis/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Bien, Cierre, Cita, Intro } from "./escenas";
import { Mejorar } from "./mejorar";
import { Clientes } from "./clientes";
import { Panel, Propuesta } from "./propuesta";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** SQL Amoblamientos con el formato del PDF: lo que hacen bien, dónde podríamos mejorar, sus asesores, la propuesta y el panel. */
export const SqlamoblamientosAnalisisVideo: React.FC = () => (
  <Montaje
    dir="proyectos/sqlamoblamientos-analisis"
    escenas={SCENES}
    componentes={{ intro: Intro, bien: Bien, cita: Cita, mejorar: Mejorar, clientes: Clientes, propuesta: Propuesta, panel: Panel, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

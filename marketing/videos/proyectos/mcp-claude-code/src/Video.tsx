import React from "react";
import dur from "../../../public/proyectos/mcp-claude-code/vo/duraciones.json";
import { Montaje } from "../../../src/comun/montaje";
import { Autenticar, Cierre, Crear, Cuenta, Equipo, Grupos, Instalar, Intro, Probar } from "./escenas";
import { INTRO_FADE, SCENES, VOICES } from "./timeline";

/** Tutorial técnico: el servidor MCP de Atentina en Claude Code (instalación, OAuth y una demo con herramientas reales). */
export const McpClaudeCodeVideo: React.FC = () => (
  <Montaje
    dir="proyectos/mcp-claude-code"
    escenas={SCENES}
    componentes={{ intro: Intro, grupos: Grupos, instalar: Instalar, autenticar: Autenticar, cuenta: Cuenta, crear: Crear, probar: Probar, equipo: Equipo, cierre: Cierre }}
    voces={VOICES}
    duraciones={dur}
    intro="intro"
    introFade={INTRO_FADE}
  />
);

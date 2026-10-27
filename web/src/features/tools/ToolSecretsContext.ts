import { createContext } from 'react';

/**
 * Los secretos que ofrece el boton Variables (los del cliente y los que ya usa la herramienta) y como crear uno
 * nuevo sin salir del editor: newSecret abre el modal y llama a onCreated con el nombre guardado.
 */
export const ToolSecretsContext = createContext<{
  names: string[];
  newSecret?: (onCreated: (name: string) => void) => void;
}>({ names: [] });

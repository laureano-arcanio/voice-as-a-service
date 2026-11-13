// Campos de texto con variables dinámicas `{{nombre}}` (docs/features/HERRAMIENTAS.md, "Variables").
//
// - `PromptEditor`: textos largos (prompt, primer mensaje, instrucciones de análisis). CodeMirror 6 bajo
//   demanda; tipear `{{` abre la lista, Enter/Tab/clic inserta `{{nombre}}`, Ctrl+Espacio la abre en cualquier
//   lugar, y cada `{{x}}` se marca: sistema (azul), declarada o asignada (verde), sin fuente (naranja).
// - `VariableField`: campos cortos (valores de herramientas, mensajes de derivación), Mantine con la misma lista.
// - Lo que ofrecen sale del catálogo `GET /variables/catalog` (filtrado por `field`, el `applies_to` de cada
//   variable), las `declared` de la definición y las `extra` que asignan el pre-call o las herramientas.
// - Una `{{x}}` sin declarar es válida (puede venir del pre-call o de una campaña): solo se avisa.
export { PromptEditor } from './PromptEditorLazy';
export type { PromptEditorProps } from './PromptEditor';
export { VariableField } from './VariableField';
export type { VariableFieldProps } from './VariableField';
export { classify, resolveVariable, useVariableCatalog, variableOptions, isSystemVariable } from './catalog';
export type {
  DeclaredVariable,
  ExtraVariable,
  VariableCatalog,
  VariableContext,
  VariableOption,
} from './catalog';
export { filter, insert, openAt, usedVariables } from './match';

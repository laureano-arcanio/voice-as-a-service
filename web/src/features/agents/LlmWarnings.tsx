import { Alert } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { ErrorList } from './ErrorList';

/** Un aviso del modelo de lenguaje: `path` para ir al campo, `code` para agrupar y el texto para el cliente. */
export interface LlmWarning {
  path: string;
  code: string;
  message: string;
}

/** Avisos al validar o guardar (app/services/llm_warnings.py): no bloquean, por eso van en amarillo. */
export function LlmWarnings({
  warnings,
  label,
  onPick,
}: {
  warnings: LlmWarning[];
  label: (path: string) => string;
  onPick: (path: string) => void;
}) {
  if (!warnings.length) return null;
  return (
    <Alert color="yellow" icon={<IconAlertTriangle size={18} />} title="Avisos del modelo de lenguaje">
      <ErrorList errors={warnings} label={label} onPick={onPick} />
    </Alert>
  );
}

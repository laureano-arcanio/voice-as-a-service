import { Skeleton } from '@mantine/core';
import { lazy, Suspense } from 'react';
import type { PromptEditorProps } from './PromptEditor';

// CodeMirror sale en un chunk aparte: solo se baja al abrir un editor de texto con variables.
const Editor = lazy(() => import('./PromptEditor'));

/** `PromptEditor` cargado bajo demanda, con un esqueleto del alto mínimo mientras llega. */
export function PromptEditor(props: PromptEditorProps) {
  return (
    <Suspense fallback={<Skeleton height={Math.round((props.minRows ?? 8) * 13 * 1.6 + 20)} radius="lg" />}>
      <Editor {...props} />
    </Suspense>
  );
}

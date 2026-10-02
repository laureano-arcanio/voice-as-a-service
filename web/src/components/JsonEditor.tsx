import { json, jsonParseLinter } from '@codemirror/lang-json';
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { linter, lintGutter } from '@codemirror/lint';
import { EditorView } from '@codemirror/view';
import { tags } from '@lezer/highlight';
import CodeMirror, { type ReactCodeMirrorRef } from '@uiw/react-codemirror';
import type { Ref } from 'react';

// Colores de la marca: claves en azul y valores en neutro. El rojo queda para los errores.
const highlight = HighlightStyle.define([
  { tag: tags.propertyName, color: 'var(--mantine-color-blue-7)' },
  { tag: tags.string, color: 'var(--mantine-color-gray-7)' },
  { tag: [tags.number, tags.bool, tags.null], color: 'var(--mantine-color-yellow-7)' },
]);

const extensions = [
  json(),
  syntaxHighlighting(highlight),
  linter(jsonParseLinter()),
  lintGutter(),
  EditorView.lineWrapping,
];

/** Editor JSON (CodeMirror). */
export function JsonEditor({
  value,
  onChange,
  readOnly = false,
  height = '520px',
  editorRef,
}: {
  value: string;
  onChange?: (v: string) => void;
  readOnly?: boolean;
  height?: string;
  editorRef?: Ref<ReactCodeMirrorRef>;
}) {
  return (
    <div className="cm-editor-wrap">
      <CodeMirror
        ref={editorRef}
        value={value}
        onChange={onChange}
        readOnly={readOnly}
        editable={!readOnly}
        height={height}
        theme="light"
        extensions={extensions}
        basicSetup={{ foldGutter: true, highlightActiveLine: !readOnly, autocompletion: false }}
        aria-label="Definición JSON"
      />
    </div>
  );
}

import { json, jsonParseLinter } from '@codemirror/lang-json';
import { linter, lintGutter } from '@codemirror/lint';
import { EditorView } from '@codemirror/view';
import { useComputedColorScheme } from '@mantine/core';
import CodeMirror, { type ReactCodeMirrorRef } from '@uiw/react-codemirror';
import type { Ref } from 'react';

const extensions = [json(), linter(jsonParseLinter()), lintGutter(), EditorView.lineWrapping];

/** Editor JSON (CodeMirror) con el tema claro/oscuro de la app. */
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
  const scheme = useComputedColorScheme('light');
  return (
    <div className="cm-editor-wrap">
      <CodeMirror
        ref={editorRef}
        value={value}
        onChange={onChange}
        readOnly={readOnly}
        editable={!readOnly}
        height={height}
        theme={scheme === 'dark' ? 'dark' : 'light'}
        extensions={extensions}
        basicSetup={{ foldGutter: true, highlightActiveLine: !readOnly, autocompletion: false }}
        aria-label="Definición JSON"
      />
    </div>
  );
}

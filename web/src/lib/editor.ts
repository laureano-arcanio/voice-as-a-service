import { EditorView } from '@codemirror/view';
import type { ReactCodeMirrorRef } from '@uiw/react-codemirror';

/** Mueve el cursor a una posicion del texto y la muestra. */
export function focusOffset(ref: ReactCodeMirrorRef | null, offset: number) {
  const view = ref?.view;
  if (!view || offset < 0) return;
  const pos = Math.min(offset, view.state.doc.length);
  view.dispatch({ selection: { anchor: pos }, effects: EditorView.scrollIntoView(pos, { y: 'center' }) });
  view.focus();
}

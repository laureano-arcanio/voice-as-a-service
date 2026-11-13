import {
  acceptCompletion,
  autocompletion,
  startCompletion,
  type CompletionContext,
  type CompletionResult,
} from '@codemirror/autocomplete';
import { RangeSetBuilder, StateEffect, StateField, type Extension } from '@codemirror/state';
import {
  Decoration,
  EditorView,
  keymap,
  placeholder as placeholderExt,
  ViewPlugin,
  type DecorationSet,
  type ViewUpdate,
} from '@codemirror/view';
import { Input, Text } from '@mantine/core';
import CodeMirror from '@uiw/react-codemirror';
import { useEffect, useMemo, useRef } from 'react';
import {
  KIND_LABEL,
  resolveVariable,
  useVariableCatalog,
  variableOptions,
  type DeclaredVariable,
  type ExtraVariable,
  type VariableCatalog,
  type VariableContext,
  type VariableSources,
} from './catalog';
import { filter, insert, openAt, variableRanges } from './match';

export interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  /** Dónde se usa el texto: decide qué variables del sistema se ofrecen. */
  field: VariableContext;
  /** Variables declaradas en la definición, en su orden. */
  declared?: DeclaredVariable[];
  /** Otras que se conocen: las que asigna el pre-call o una herramienta. */
  extra?: ExtraVariable[];
  /** Catálogo ya cargado; sin él se pide a `GET /variables/catalog`. */
  catalog?: VariableCatalog | null;
  maxLength?: number;
  /** Alto mínimo en líneas (8) y máximo en px (520); pasado el máximo, scroll. */
  minRows?: number;
  maxHeight?: number | string;
  label?: string;
  description?: string;
  error?: string;
  placeholder?: string;
  readOnly?: boolean;
}

/** Fuentes de variables del campo, dentro del estado del editor (las lee el marcado y el autocompletado). */
const setSources = StateEffect.define<VariableSources>();
const sourcesField = StateField.define<VariableSources>({
  create: () => ({ field: 'prompt' }),
  update(value, tr) {
    for (const e of tr.effects) if (e.is(setSources)) return e.value;
    return value;
  },
});
const HEADING = /^#{1,6}(\s|$)/;
const lineHeading = Decoration.line({ class: 'cm-var-h' });

/** Marca `{{x}}` según de dónde viene y los títulos `#`, solo en lo visible. */
function markPlugin() {
  const build = (view: EditorView): DecorationSet => {
    const b = new RangeSetBuilder<Decoration>();
    const sources = view.state.field(sourcesField);
    const doc = view.state.doc;
    let last = -1;
    for (const r of view.visibleRanges) {
      for (let pos = r.from; pos <= r.to;) {
        const line = doc.lineAt(pos);
        pos = line.to + 1;
        if (line.from <= last) continue;
        last = line.from;
        if (HEADING.test(line.text)) b.add(line.from, line.from, lineHeading);
        for (const m of variableRanges(line.text)) {
          const res = resolveVariable(m.name, sources);
          const tip = res.kind === 'system' ? `Sistema. ${res.description}` : res.description;
          const title = res.kind === 'declared' && !res.description ? 'Variable declarada' : tip;
          b.add(
            line.from + m.from,
            line.from + m.to,
            Decoration.mark({ class: `cm-var cm-var-${res.kind}`, attributes: { title } }),
          );
        }
      }
    }
    return b.finish();
  };
  return ViewPlugin.fromClass(
    class {
      decorations: DecorationSet;
      constructor(view: EditorView) {
        this.decorations = build(view);
      }
      update(u: ViewUpdate) {
        if (
          u.docChanged ||
          u.viewportChanged ||
          u.transactions.some((t) => t.effects.some((e) => e.is(setSources)))
        ) {
          this.decorations = build(u.view);
        }
      }
    },
    { decorations: (p) => p.decorations },
  );
}

/** Fuente del autocompletado: se abre con `{{` (o Ctrl+Espacio) y aplica `match.insert`. */
function variableSource() {
  return (ctx: CompletionContext): CompletionResult | null => {
    const line = ctx.state.doc.lineAt(ctx.pos);
    const cursor = ctx.pos - line.from;
    const open = openAt(line.text, cursor);
    if (!open && !ctx.explicit) return null;
    const options = filter(variableOptions(ctx.state.field(sourcesField)), open?.query ?? '');
    if (!options.length) return null;
    return {
      from: line.from + (open ? open.from : cursor),
      filter: false,
      options: options.map((o) => ({
        label: o.name,
        detail: KIND_LABEL[o.kind],
        type: 'variable',
        info: o.description ? `${o.description}${o.example ? ` (ej.: ${o.example})` : ''}` : undefined,
        apply: (view, _c, from, to) => {
          const l = view.state.doc.lineAt(to);
          const r = insert(l.text, from - l.from, to - l.from, o.insertName, o.partial);
          view.dispatch({
            changes: { from: l.from + r.from, to: l.from + r.to, insert: r.inserted },
            selection: { anchor: l.from + r.cursor },
            userEvent: 'input.complete',
          });
          // Un nombre con hueco (`fields.`) sigue abierto: se ofrece lo que sigue.
          if (o.partial) startCompletion(view);
        },
      })),
    };
  };
}

const theme = EditorView.theme({
  '&': {
    border: '1px solid var(--pe-border, var(--app-line))',
    borderRadius: 'var(--mantine-radius-lg)',
    backgroundColor: 'var(--mantine-color-body)',
    color: 'var(--mantine-color-text)',
  },
  '&.cm-focused': { outline: 'none', borderColor: 'var(--pe-focus, var(--mantine-color-blue-6))' },
  '.cm-scroller': {
    fontFamily: 'var(--mantine-font-family-monospace)',
    fontSize: '13px',
    lineHeight: '1.6',
    borderRadius: 'var(--mantine-radius-lg)',
  },
  '.cm-content': { padding: '10px 12px', caretColor: 'var(--mantine-color-text)' },
  '.cm-line': { padding: 0 },
  '.cm-placeholder': { color: 'var(--mantine-color-dimmed)' },
  '.cm-var-h': { fontWeight: 700 },
  '.cm-var': { borderRadius: '4px', padding: '0 2px' },
  '.cm-var-system': { color: 'var(--mantine-color-blue-7)', backgroundColor: 'var(--mantine-color-blue-0)' },
  '.cm-var-declared': {
    color: 'var(--mantine-color-green-7)',
    backgroundColor: 'var(--mantine-color-green-0)',
  },
  '.cm-var-unknown': {
    color: 'var(--mantine-color-yellow-8)',
    backgroundColor: 'var(--mantine-color-yellow-0)',
    textDecoration: 'underline dotted',
  },
  '.cm-tooltip': {
    border: '1px solid var(--app-line)',
    borderRadius: 'var(--mantine-radius-md)',
    backgroundColor: 'var(--mantine-color-body)',
    boxShadow: 'var(--mantine-shadow-md)',
  },
  '.cm-tooltip.cm-tooltip-autocomplete > ul': {
    fontFamily: 'var(--mantine-font-family-monospace)',
    fontSize: '12px',
    maxHeight: '240px',
  },
  '.cm-tooltip-autocomplete ul li[aria-selected]': {
    backgroundColor: 'var(--mantine-color-blue-light)',
    color: 'var(--mantine-color-blue-light-color)',
  },
  '.cm-completionDetail': { fontStyle: 'normal', color: 'var(--mantine-color-dimmed)', marginLeft: '1em' },
  '.cm-completionInfo': { fontFamily: 'var(--mantine-font-family)', fontSize: '12px', maxWidth: '280px' },
});

const baseExtensions: Extension[] = [
  sourcesField,
  theme,
  EditorView.lineWrapping,
  markPlugin(),
  autocompletion({ override: [variableSource()], icons: false, activateOnTyping: true }),
  // Tab acepta la opción si la lista está abierta; si no, sigue su camino (mover el foco).
  keymap.of([{ key: 'Tab', run: acceptCompletion }]),
];

const BASIC_SETUP = {
  lineNumbers: false,
  foldGutter: false,
  highlightActiveLine: false,
  highlightActiveLineGutter: false,
  highlightSelectionMatches: false,
  autocompletion: false,
  closeBrackets: false,
  bracketMatching: false,
  indentOnInput: false,
  rectangularSelection: false,
  crosshairCursor: false,
} as const;

const fmt = (n: number) => n.toLocaleString('es-AR');

/**
 * Editor de textos largos con variables (CodeMirror 6): al tipear `{{` ofrece las del sistema que aplican al
 * campo, las declaradas y las asignadas por herramientas; marca cada `{{x}}` por su origen. Se carga con
 * `lazy` desde `./index`.
 */
export default function PromptEditor({
  value,
  onChange,
  field,
  declared,
  extra,
  catalog: catalogProp,
  maxLength,
  minRows = 8,
  maxHeight = 520,
  label,
  description,
  error,
  placeholder,
  readOnly = false,
}: PromptEditorProps) {
  const query = useVariableCatalog(!catalogProp);
  const catalog = catalogProp ?? query.data;
  const viewRef = useRef<EditorView | null>(null);

  // Las fuentes pasan al editor solo si cambiaron (no en cada tecla).
  const signature = JSON.stringify([field, declared, extra]);
  const sources = useMemo<VariableSources>(
    () => ({ catalog, declared, extra, field }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `declared` y `extra` llegan como arrays nuevos
    [catalog, signature],
  );
  useEffect(() => {
    viewRef.current?.dispatch({ effects: setSources.of(sources) });
  }, [sources]);

  const extensions = useMemo(
    () => [
      ...baseExtensions,
      EditorView.contentAttributes.of({ 'aria-label': label ?? 'Texto con variables' }),
      ...(placeholder ? [placeholderExt(placeholder)] : []),
    ],
    [label, placeholder],
  );

  const length = Array.from(value).length;
  const over = maxLength !== undefined && length > maxLength;
  const rowsPx = `${Math.round(minRows * 13 * 1.6 + 20)}px`;

  return (
    <Input.Wrapper label={label} description={description} error={error}>
      <div
        data-testid="prompt-editor"
        style={error ? ({ '--pe-border': 'var(--mantine-color-error)' } as React.CSSProperties) : undefined}
      >
        <CodeMirror
          value={value}
          onChange={onChange}
          onCreateEditor={(view) => {
            viewRef.current = view;
            view.dispatch({ effects: setSources.of(sources) });
          }}
          readOnly={readOnly}
          editable={!readOnly}
          minHeight={rowsPx}
          maxHeight={typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight}
          theme="light"
          extensions={extensions}
          basicSetup={BASIC_SETUP}
          indentWithTab={false}
        />
      </div>
      {maxLength !== undefined && (
        <Text size="xs" ta="right" mt={4} c={over ? 'red' : 'dimmed'} data-testid="prompt-counter">
          {fmt(length)} / {fmt(maxLength)}
        </Text>
      )}
    </Input.Wrapper>
  );
}

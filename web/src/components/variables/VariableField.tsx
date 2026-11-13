import { Combobox, Group, Text, Textarea, TextInput, useCombobox } from '@mantine/core';
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
  type ReactNode,
} from 'react';
import {
  KIND_LABEL,
  classify,
  useVariableCatalog,
  variableOptions,
  type DeclaredVariable,
  type ExtraVariable,
  type VariableCatalog,
  type VariableContext,
  type VariableOption,
} from './catalog';
import { filter, insert, openAt, usedVariables, type OpenMatch } from './match';

export interface VariableFieldProps {
  value: string;
  onChange: (value: string) => void;
  /** Dónde se usa el texto: decide qué variables del sistema se ofrecen. */
  field: VariableContext;
  declared?: DeclaredVariable[];
  extra?: ExtraVariable[];
  /** Catálogo ya cargado; sin él se pide a `GET /variables/catalog`. */
  catalog?: VariableCatalog | null;
  /** Si la lista puede abrirse en esta posición (la URL no lleva variables antes del path). */
  opensAt?: (text: string, cursor: number) => boolean;
  /** Varias líneas (`Textarea` con alto automático) en vez de `TextInput`. */
  multiline?: boolean;
  minRows?: number;
  maxRows?: number;
  label?: ReactNode;
  description?: ReactNode;
  placeholder?: string;
  error?: ReactNode;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  size?: 'xs' | 'sm' | 'md';
  maxLength?: number;
  'aria-label'?: string;
}

/**
 * Campo corto con variables: al tipear `{{` abre la lista (sistema, declaradas, asignadas), filtra mientras se
 * escribe y Enter, Tab o clic insertan `{{nombre}}`. Debajo avisa las `{{x}}` sin fuente conocida.
 */
export function VariableField({
  value,
  onChange,
  field,
  declared,
  extra,
  catalog: catalogProp,
  opensAt,
  multiline = false,
  minRows,
  maxRows,
  label,
  description,
  placeholder,
  error,
  disabled,
  readOnly,
  required,
  size,
  maxLength,
  'aria-label': ariaLabel,
}: VariableFieldProps) {
  const query = useVariableCatalog(!catalogProp);
  const catalog = catalogProp ?? query.data;
  const sources = useMemo(() => ({ catalog, declared, extra, field }), [catalog, declared, extra, field]);
  const options = useMemo(() => variableOptions(sources), [sources]);

  const combobox = useCombobox({ onDropdownClose: () => combobox.resetSelectedOption() });
  const [open, setOpen] = useState<OpenMatch | null>(null);
  const el = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  const pendingCursor = useRef<number | null>(null);

  const shown = useMemo(() => (open ? filter(options, open.query) : []), [open, options]);
  const visible = !!open && shown.length > 0 && !disabled && !readOnly;

  // Abrir o cerrar la lista según el cursor, y dejar la primera opción elegida (Enter/Tab la inserta).
  useEffect(() => {
    if (visible) {
      combobox.openDropdown();
      combobox.selectFirstOption();
    } else combobox.closeDropdown();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `combobox` cambia en cada render
  }, [visible, open?.query, shown.length]);

  // Tras insertar, el cursor va al final de lo insertado (el valor se aplica en el render siguiente).
  useEffect(() => {
    if (pendingCursor.current !== null && el.current) {
      el.current.setSelectionRange(pendingCursor.current, pendingCursor.current);
      pendingCursor.current = null;
    }
  }, [value]);

  const track = (target: HTMLInputElement | HTMLTextAreaElement) => {
    el.current = target;
    const cursor = target.selectionStart ?? target.value.length;
    setOpen(opensAt && !opensAt(target.value, cursor) ? null : openAt(target.value, cursor));
  };

  const apply = (name: string) => {
    const opt = options.find((o) => o.name === name);
    if (!opt || !open || !el.current) return;
    const cursor = el.current.selectionStart ?? value.length;
    const r = insert(value, open.from, cursor, opt.insertName, opt.partial);
    pendingCursor.current = r.cursor;
    onChange(r.text);
    // Un nombre con hueco (`fields.`) sigue abierto: la lista ofrece lo que sigue.
    setOpen(opt.partial ? { from: open.from, query: opt.insertName } : null);
    el.current.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (!visible) return;
    // Enter y las flechas las resuelve el Combobox; Tab inserta la elegida (o la primera).
    if (e.key === 'Tab' && !e.shiftKey) {
      const idx = combobox.getSelectedOptionIndex();
      const opt = shown[idx >= 0 ? idx : 0];
      if (opt) {
        e.preventDefault();
        apply(opt.name);
      }
    }
  };

  const onInputChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onChange(e.currentTarget.value);
    track(e.currentTarget);
  };

  const common = {
    value,
    onChange: onInputChange,
    onClick: (e: React.MouseEvent<HTMLInputElement | HTMLTextAreaElement>) => track(e.currentTarget),
    onKeyUp: (e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) track(e.currentTarget);
    },
    onKeyDown,
    onBlur: () => setOpen(null),
    label,
    description,
    placeholder,
    error,
    disabled,
    readOnly,
    required,
    size,
    maxLength,
    'aria-label': ariaLabel,
    autoComplete: 'off',
  };

  const unknown = useMemo(
    () => usedVariables(value).filter((n) => classify(n, sources) === 'unknown'),
    [value, sources],
  );

  return (
    <div>
      <Combobox store={combobox} onOptionSubmit={apply} withinPortal position="bottom-start">
        <Combobox.Target>
          {multiline ? (
            <Textarea {...common} autosize minRows={minRows ?? 2} maxRows={maxRows ?? 8} />
          ) : (
            <TextInput {...common} />
          )}
        </Combobox.Target>
        <Combobox.Dropdown hidden={!visible}>
          <Combobox.Options mah={240} style={{ overflowY: 'auto' }}>
            {shown.map((o) => (
              <Combobox.Option key={o.name} value={o.name}>
                <OptionRow option={o} />
              </Combobox.Option>
            ))}
          </Combobox.Options>
        </Combobox.Dropdown>
      </Combobox>
      {unknown.length > 0 && (
        <Text size="xs" c="yellow.8" mt={4} data-testid="unknown-variables">
          Sin fuente declarada: {unknown.map((n) => `{{${n}}}`).join(', ')}. Pueden venir del pre-call o de
          una herramienta; si nadie las asigna, quedan vacías.
        </Text>
      )}
    </div>
  );
}

function OptionRow({ option }: { option: VariableOption }) {
  return (
    <div>
      <Group justify="space-between" gap="md" wrap="nowrap">
        <Text size="sm" ff="monospace">
          {option.name}
        </Text>
        <Text size="xs" c="dimmed">
          {KIND_LABEL[option.kind]}
        </Text>
      </Group>
      {option.description && (
        <Text size="xs" c="dimmed">
          {option.description}
          {option.example ? ` (ej.: ${option.example})` : ''}
        </Text>
      )}
    </div>
  );
}

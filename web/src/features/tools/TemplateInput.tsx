import { Button, Menu, TextInput, type TextInputProps } from '@mantine/core';
import { IconChevronDown, IconPlus, IconVariable } from '@tabler/icons-react';
import { useContext, useRef } from 'react';
import { SECRET_RE, TEMPLATE_VARS } from './draft';
import { ToolSecretsContext } from './ToolSecretsContext';

/** Ancho del boton "Variables" dentro del campo (rightSection). */
const MENU_WIDTH = 118;

/**
 * Boton "Variables" con el menu de secretos y variables. Con onVar inserta {{secrets.X}} o {{call.from}}
 * donde esta el cursor; sin onVar (campo que lleva solo el nombre de un secreto) lista solo los secretos.
 */
export function VariablesMenu({
  onSecret,
  onVar,
}: {
  onSecret: (name: string) => void;
  onVar?: (v: string) => void;
}) {
  const { names: secrets, newSecret } = useContext(ToolSecretsContext);
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <Button
          variant="light"
          size="compact-xs"
          leftSection={<IconVariable size={14} />}
          rightSection={<IconChevronDown size={12} />}
          aria-label="Variables"
        >
          Variables
        </Button>
      </Menu.Target>
      <Menu.Dropdown mah={360} style={{ overflowY: 'auto' }}>
        <Menu.Label>Secretos</Menu.Label>
        {secrets.length === 0 && <Menu.Label>Todavía no cargaste secretos.</Menu.Label>}
        {secrets.map((s) => (
          <Menu.Item key={s} className="mono" onClick={() => onSecret(s)}>
            {onVar ? `{{secrets.${s}}}` : s}
          </Menu.Item>
        ))}
        {newSecret && (
          <Menu.Item leftSection={<IconPlus size={14} />} onClick={() => newSecret(onSecret)}>
            Nuevo secreto
          </Menu.Item>
        )}
        {onVar &&
          TEMPLATE_VARS.map((g) => (
            <div key={g.group}>
              <Menu.Divider />
              <Menu.Label>{g.group}</Menu.Label>
              {g.items.map((v) => (
                <Menu.Item
                  key={v.value}
                  onClick={() => onVar(v.value)}
                  rightSection={<span className="mono">{v.value}</span>}
                >
                  {v.label}
                </Menu.Item>
              ))}
            </div>
          ))}
      </Menu.Dropdown>
    </Menu>
  );
}

/** Campo de texto para un valor fijo, con el boton de variables a la derecha. */
export function TemplateInput({
  value,
  onChange,
  ...props
}: Omit<TextInputProps, 'value' | 'onChange'> & {
  value: string;
  onChange: (v: string) => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const insert = (v: string) => {
    const el = ref.current;
    const at = el?.selectionStart ?? value.length;
    const end = el?.selectionEnd ?? at;
    onChange(value.slice(0, at) + v + value.slice(end));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(at + v.length, at + v.length);
    });
  };
  return (
    <TextInput
      ref={ref}
      {...props}
      classNames={{ input: 'mono' }}
      value={value}
      onChange={(e) => onChange(e.currentTarget.value)}
      rightSectionWidth={MENU_WIDTH}
      rightSectionPointerEvents="all"
      rightSection={<VariablesMenu onSecret={(s) => insert(`{{secrets.${s}}}`)} onVar={insert} />}
    />
  );
}

/** Campo con el nombre de un secreto (CRM_TOKEN), con el mismo boton de variables (solo secretos). */
export function SecretInput({
  value,
  onChange,
  ...props
}: Omit<TextInputProps, 'value' | 'onChange'> & {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <TextInput
      {...props}
      classNames={{ input: 'mono' }}
      value={value}
      // Si pegan {{secrets.X}}, queda X.
      onChange={(e) =>
        onChange(e.currentTarget.value.replace(/^\{\{\s*secrets\.|\s*\}\}$/g, '').toUpperCase())
      }
      error={value && !SECRET_RE.test(value) ? 'Mayúsculas, números y _ (ej. CRM_TOKEN)' : undefined}
      rightSectionWidth={MENU_WIDTH}
      rightSectionPointerEvents="all"
      rightSection={<VariablesMenu onSecret={onChange} />}
    />
  );
}

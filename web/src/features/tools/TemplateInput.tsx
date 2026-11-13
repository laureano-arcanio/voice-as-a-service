import { Button, Menu, TextInput, type TextInputProps } from '@mantine/core';
import { IconChevronDown, IconPlus, IconVariable } from '@tabler/icons-react';
import { useContext, useMemo } from 'react';
import { VariableField, type VariableFieldProps } from '@/components/variables';
import { SECRET_RE } from './draft';
import { ToolSecretsContext } from './ToolSecretsContext';

/** Ancho del boton "Variables" dentro del campo (rightSection). */
const MENU_WIDTH = 118;

/**
 * Boton "Variables" con el menu de secretos. Con onSecret inserta {{secrets.X}} o el nombre donde esta el
 * cursor; el campo que lleva solo el nombre de un secreto lista solo los secretos.
 */
export function VariablesMenu({
  onSecret,
}: {
  onSecret: (name: string) => void;
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
            {s}
          </Menu.Item>
        ))}
        {newSecret && (
          <Menu.Item leftSection={<IconPlus size={14} />} onClick={() => newSecret(onSecret)}>
            Nuevo secreto
          </Menu.Item>
        )}
      </Menu.Dropdown>
    </Menu>
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

/**
 * Campo de una herramienta que acepta templates (valor fijo, header, URL, autenticación): al tipear `{{`
 * ofrece las variables que aplican a una herramienta y los secretos del cliente por nombre.
 */
export function ToolVariableField({ extra = [], ...props }: Omit<VariableFieldProps, 'field'>) {
  const { names } = useContext(ToolSecretsContext);
  const all = useMemo(
    () => [
      ...names.map((name) => ({
        name: `secrets.${name}`,
        description: 'Secreto de la cuenta o del agente',
        kind: 'secret' as const,
      })),
      ...extra,
    ],
    [names, extra],
  );
  return <VariableField field="tool" extra={all} {...props} />;
}

import {
  ActionIcon,
  Button,
  Checkbox,
  Group,
  SegmentedControl,
  Select,
  Stack,
  TagsInput,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { blankParam, PARAM_TYPES, type ParamRow, type ParamType } from './draft';
import { TemplateInput } from './TemplateInput';

/**
 * Filas de parametros: nombre, tipo, quien lo completa (el agente o un valor fijo) y su descripcion o valor.
 * Sirve para la ruta, la query y el body de una herramienta HTTP y para los parametros del codigo.
 */
export function ParamsEditor({
  rows,
  onChange,
  allowFixed = true,
  showRequired = true,
  fixedNames = false,
  secrets = [],
  addLabel = 'Agregar parámetro',
  empty,
  label = 'Parámetro',
}: {
  rows: ParamRow[];
  onChange: (rows: ParamRow[]) => void;
  /** Con false, todos los completa el agente (parametros del codigo). */
  allowFixed?: boolean;
  /** Mostrar "Obligatorio" (la ruta lo es siempre). */
  showRequired?: boolean;
  /** Los nombres salen de otro lado (las {variables} de la URL): no se agregan, renombran ni quitan. */
  fixedNames?: boolean;
  /** Secretos para el menu de variables de los valores fijos. */
  secrets?: string[];
  addLabel?: string;
  empty?: string;
  /** Para los aria-label: "Parámetro", "Campo". */
  label?: string;
}) {
  const set = (key: string, patch: Partial<ParamRow>) =>
    onChange(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  const names = rows.map((r) => r.name.trim()).filter(Boolean);

  return (
    <Stack gap="xs">
      {rows.length === 0 && empty && (
        <Text size="sm" c="dimmed">
          {empty}
        </Text>
      )}
      {rows.map((r, i) => {
        const fixed = r.source === 'fixed';
        const dup = r.name.trim() && names.filter((n) => n === r.name.trim()).length > 1;
        const n = r.name || `${label.toLowerCase()} ${i + 1}`;
        return (
          <div key={r.key} className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
            <Group gap="xs" align="flex-start" wrap="nowrap">
              <Group gap="xs" align="flex-start" wrap="wrap" style={{ flex: 1, minWidth: 0 }}>
                <TextInput
                  aria-label={`Nombre del ${label.toLowerCase()} ${i + 1}`}
                  placeholder="dni"
                  value={r.name}
                  readOnly={fixedNames}
                  onChange={(e) => set(r.key, { name: e.currentTarget.value })}
                  error={dup ? 'Repetido' : undefined}
                  classNames={{ input: 'mono' }}
                  w={{ base: '100%', xs: 170 }}
                />
                <Select
                  aria-label={`Tipo de ${n}`}
                  data={PARAM_TYPES.filter((t) => !fixedNames || t.value !== 'array')}
                  value={r.type}
                  onChange={(v) => v && set(r.key, { type: v as ParamType })}
                  allowDeselect={false}
                  w={120}
                />
                {allowFixed && (
                  <SegmentedControl
                    aria-label={`Quién completa ${n}`}
                    value={r.source}
                    onChange={(v) => set(r.key, { source: v as ParamRow['source'] })}
                    data={[
                      { value: 'agent', label: 'El agente' },
                      { value: 'fixed', label: 'Valor fijo' },
                    ]}
                  />
                )}
                {showRequired && !fixed && (
                  <Checkbox
                    mt={8}
                    label="Obligatorio"
                    checked={r.required}
                    onChange={(e) => set(r.key, { required: e.currentTarget.checked })}
                  />
                )}
              </Group>
              {!fixedNames && (
                <Tooltip label="Quitar" withArrow>
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    mt={4}
                    aria-label={`Quitar ${n}`}
                    onClick={() => onChange(rows.filter((x) => x.key !== r.key))}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Tooltip>
              )}
            </Group>
            {fixed ? (
              <TemplateInput
                mt="xs"
                aria-label={`Valor de ${n}`}
                description={
                  r.type === 'array'
                    ? 'Separado por comas. Puede llevar variables.'
                    : 'Siempre se manda este valor; el agente no lo ve. Puede llevar variables.'
                }
                placeholder="{{call.from}}"
                value={r.value}
                onChange={(value) => set(r.key, { value })}
                secrets={secrets}
              />
            ) : (
              <Group mt="xs" gap="xs" align="flex-start" wrap="wrap">
                <TextInput
                  style={{ flex: 1, minWidth: 220 }}
                  aria-label={`Descripción de ${n}`}
                  description="Para el agente: qué es y en qué formato."
                  placeholder="DNI de la persona, sin puntos"
                  value={r.description}
                  onChange={(e) => set(r.key, { description: e.currentTarget.value })}
                />
                {r.type !== 'boolean' && r.type !== 'array' && (
                  <TagsInput
                    w={{ base: '100%', xs: 220 }}
                    aria-label={`Valores posibles de ${n}`}
                    description="Valores posibles (opcional)"
                    placeholder="Enter para agregar"
                    value={r.options}
                    onChange={(options) => set(r.key, { options })}
                  />
                )}
              </Group>
            )}
          </div>
        );
      })}
      {!fixedNames && (
        <Button
          variant="default"
          size="xs"
          leftSection={<IconPlus size={16} />}
          onClick={() => onChange([...rows, blankParam()])}
          style={{ alignSelf: 'flex-start' }}
        >
          {addLabel}
        </Button>
      )}
    </Stack>
  );
}

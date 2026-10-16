import { ActionIcon, Button, Group, Menu, NumberInput, Select, Stack, Switch, Text, Tooltip } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import type { LlmParamSpec } from '@/api/types';
import { blankParam, type ParamDraft } from './draft';

export type LocalDefaults = Record<string, Record<string, unknown>>;

interface Props {
  /** Filas del borrador (lo que se manda). */
  rows: ParamDraft[];
  /** Proveedor cuyos parametros se ofrecen para agregar. */
  provider: string;
  /** Motor: elige los defaults del LLM local (voz vs. assistant). */
  engine: string;
  /** El catalogo completo, por proveedor (GET /llm/params). */
  providers: { kind: string; label: string; params: LlmParamSpec[] }[];
  localDefaults: LocalDefaults;
  onChange: (rows: ParamDraft[]) => void;
  compact?: boolean;
}

/** Valor con el que arranca un parametro nuevo: el del LLM local si es de los suyos, si no el default
 * tipico (primer choice o vacio). */
function defaultFor(spec: LlmParamSpec, provider: string, engine: string, localDefaults: LocalDefaults) {
  const local = provider === 'vllm' ? localDefaults[engine]?.[spec.name] : undefined;
  if (typeof local === 'string' || typeof local === 'number' || typeof local === 'boolean') return local;
  if (spec.type === 'bool') return false;
  if (spec.type === 'choice') return spec.choices?.[0] ?? '';
  return '';
}

const valueInput = (spec: LlmParamSpec, value: string | number | boolean, onChange: (v: string | number | boolean) => void) => {
  if (spec.type === 'bool') {
    return <Switch checked={value === true} onChange={(e) => onChange(e.currentTarget.checked)} />;
  }
  if (spec.type === 'choice') {
    return (
      <Select
        data={spec.choices ?? []}
        value={typeof value === 'string' ? value : null}
        onChange={(v) => onChange(v ?? '')}
        allowDeselect={false}
        w={150}
        comboboxProps={{ withinPortal: true }}
      />
    );
  }
  return (
    <NumberInput
      value={value === '' ? '' : Number(value)}
      onChange={(v) => onChange(v === '' || v === undefined ? '' : v)}
      min={spec.minimum ?? undefined}
      max={spec.maximum ?? undefined}
      step={spec.type === 'number' ? 0.1 : 1}
      decimalScale={spec.type === 'number' ? 2 : 0}
      allowDecimal={spec.type === 'number'}
      placeholder="valor"
      w={150}
    />
  );
};

/** Editor de parametros de generacion: se agregan y quitan de la lista de los que se mandan. Cada
 * proveedor ofrece los suyos (top_k solo el local; effort solo Anthropic) con sus defaults. */
export function GenerationEditor({ rows, provider, engine, providers, localDefaults, onChange, compact }: Props) {
  const catalog = providers.find((p) => p.kind === provider)?.params ?? [];
  const all = new Map(providers.flatMap((p) => p.params).map((s) => [s.name, s]));
  const used = new Set(rows.map((r) => r.name));
  const available = catalog.filter((s) => !used.has(s.name));

  const patch = (key: string, value: string | number | boolean) =>
    onChange(rows.map((r) => (r.key === key ? { ...r, value } : r)));
  const remove = (key: string) => onChange(rows.filter((r) => r.key !== key));

  return (
    <Stack gap="xs">
      {rows.map((row) => {
        const spec = all.get(row.name);
        const applies = catalog.some((s) => s.name === row.name);
        return (
          <Group key={row.key} align="flex-end" gap="sm" wrap="wrap">
            <Stack gap={0} style={{ flex: '1 1 200px' }}>
              <Text size="sm">{spec?.label ?? row.name}</Text>
              {!compact && spec?.hint && <Text size="xs" c="dimmed">{spec.hint}</Text>}
              {!applies && (
                <Text size="xs" c="dimmed">No aplica a {provider}: se descarta.</Text>
              )}
            </Stack>
            {spec ? valueInput(spec, row.value, (v) => patch(row.key, v)) : null}
            <Tooltip label="Quitar parámetro" withArrow>
              <ActionIcon color="red" variant="subtle" aria-label="Quitar parámetro" onClick={() => remove(row.key)}>
                <IconTrash size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        );
      })}
      {available.length > 0 && (
        <Menu position="bottom-start" withinPortal>
          <Menu.Target>
            <Button variant="default" size="xs" leftSection={<IconPlus size={16} />} w="fit-content">
              Agregar parámetro
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            {available.map((spec) => (
              <Menu.Item key={spec.name} onClick={() => onChange([...rows, blankParam(spec.name, defaultFor(spec, provider, engine, localDefaults))])}>
                {spec.label}
              </Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>
      )}
    </Stack>
  );
}

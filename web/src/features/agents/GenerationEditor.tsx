import {
  ActionIcon,
  Badge,
  Button,
  Collapse,
  Group,
  NumberInput,
  Select,
  Stack,
  Switch,
  Text,
  Tooltip,
} from '@mantine/core';
import {
  IconAdjustmentsHorizontal,
  IconArrowBackUp,
  IconChevronDown,
  IconLock,
  IconTrash,
} from '@tabler/icons-react';
import { useState } from 'react';
import type { LlmParamSpec } from '@/api/types';
import { blankParam, type ParamDraft } from './draft';

export type ParamValue = string | number | boolean;

/** Sin default conocido: lo decide el modelo o el proveedor. */
const AUTO = 'Automático';

interface Props {
  /** Los parametros cambiados (lo que se manda). Los que no estan usan el default. */
  rows: ParamDraft[];
  /** Los parametros que se muestran, en orden. */
  specs: LlmParamSpec[];
  /** Todo el catalogo, para nombrar los cambiados que no aplican. */
  allSpecs: Map<string, LlmParamSpec>;
  /** Valor por defecto conocido de cada parametro (el del servidor propio o el de un nivel de arriba). */
  defaults: Record<string, unknown>;
  /** Editable: ya se confirmo el cambio. */
  unlocked: boolean;
  onUnlock: () => void;
  onChange: (rows: ParamDraft[]) => void;
  /** Texto del boton que despliega la lista. */
  label: string;
  /** Por que un parametro cambiado no aplica (p. ej. "No lo usa Anthropic: se descarta."). */
  notApplies: string;
}

const isValue = (v: unknown): v is ParamValue =>
  typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean';

function show(v: ParamValue): string {
  if (typeof v === 'boolean') return v ? 'Sí' : 'No';
  return String(v);
}

function ValueInput({
  spec,
  value,
  fallback,
  disabled,
  onChange,
}: {
  spec: LlmParamSpec;
  value: ParamValue | undefined;
  fallback: ParamValue | undefined;
  disabled: boolean;
  onChange: (v: ParamValue | null) => void;
}) {
  const shown = value ?? fallback;
  const aria = { 'aria-label': spec.label };
  if (spec.type === 'bool') {
    if (fallback !== undefined) {
      return (
        <Switch
          {...aria}
          checked={shown === true}
          disabled={disabled}
          onChange={(e) => onChange(e.currentTarget.checked)}
        />
      );
    }
    return (
      <Select
        {...aria}
        data={[
          { value: '', label: AUTO },
          { value: 'true', label: 'Sí' },
          { value: 'false', label: 'No' },
        ]}
        value={shown === undefined ? '' : String(shown)}
        onChange={(v) => onChange(v === 'true' ? true : v === 'false' ? false : null)}
        allowDeselect={false}
        disabled={disabled}
        w={150}
        comboboxProps={{ withinPortal: true }}
      />
    );
  }
  if (spec.type === 'choice') {
    return (
      <Select
        {...aria}
        data={spec.choices ?? []}
        value={typeof shown === 'string' ? shown : null}
        onChange={(v) => onChange(v)}
        placeholder={AUTO}
        clearable={fallback === undefined}
        allowDeselect={false}
        disabled={disabled}
        w={150}
        comboboxProps={{ withinPortal: true }}
      />
    );
  }
  return (
    <NumberInput
      {...aria}
      value={shown === undefined ? '' : Number(shown)}
      onChange={(v) => onChange(v === '' || v === undefined ? null : v)}
      min={spec.minimum ?? undefined}
      max={spec.maximum ?? undefined}
      step={spec.type === 'number' ? 0.1 : 1}
      decimalScale={spec.type === 'number' ? 2 : 0}
      allowDecimal={spec.type === 'number'}
      placeholder={AUTO}
      disabled={disabled}
      w={150}
    />
  );
}

/** Parametros de generacion: muestra todos los del proveedor con su valor por defecto y deja cambiarlos
 * (despues de confirmar). Solo los cambiados van a la definicion; volver al default los saca. */
export function GenerationEditor({
  rows,
  specs,
  allSpecs,
  defaults,
  unlocked,
  onUnlock,
  onChange,
  label,
  notApplies,
}: Props) {
  const [open, setOpen] = useState(rows.length > 0);
  const byName = new Map(rows.map((r) => [r.name, r]));
  const shownNames = new Set(specs.map((s) => s.name));
  const orphans = rows.filter((r) => !shownNames.has(r.name));

  const set = (spec: LlmParamSpec, v: ParamValue | null) => {
    const def = defaults[spec.name];
    const rest = rows.filter((r) => r.name !== spec.name);
    if (v === null || v === '' || v === def) return onChange(rest);
    const prev = byName.get(spec.name);
    onChange(
      prev
        ? rows.map((r) => (r.name === spec.name ? { ...r, value: v } : r))
        : [...rows, blankParam(spec.name, v)],
    );
  };
  const remove = (name: string) => onChange(rows.filter((r) => r.name !== name));

  return (
    <Stack gap="xs">
      <Group gap="xs">
        <Button
          variant="subtle"
          size="xs"
          px={4}
          leftSection={<IconAdjustmentsHorizontal size={16} />}
          rightSection={
            <IconChevronDown size={14} style={{ transform: open ? 'rotate(180deg)' : undefined }} />
          }
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          {label}
        </Button>
        {rows.length > 0 && (
          <Badge variant="light" color="orange" size="sm">
            {rows.length === 1 ? '1 cambiado' : `${rows.length} cambiados`}
          </Badge>
        )}
      </Group>

      <Collapse in={open}>
        <Stack gap="sm" className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
          <Group justify="space-between" gap="sm" wrap="wrap">
            <Text size="xs" c="dimmed" style={{ flex: '1 1 260px' }}>
              {unlocked
                ? 'Lo que no cambies usa el valor por defecto. Volver al default saca el cambio.'
                : 'Estos son los valores por defecto, los recomendados para este modelo.'}
            </Text>
            {!unlocked && (
              <Button variant="default" size="xs" leftSection={<IconLock size={14} />} onClick={onUnlock}>
                Cambiar valores
              </Button>
            )}
          </Group>

          {specs.map((spec) => {
            const row = byName.get(spec.name);
            const def = defaults[spec.name];
            const fallback = isValue(def) ? def : undefined;
            return (
              <Group key={spec.name} align="center" gap="sm" wrap="wrap">
                <Stack gap={0} style={{ flex: '1 1 220px' }}>
                  <Group gap={6}>
                    <Text size="sm">{spec.label}</Text>
                    {row ? (
                      <Badge variant="light" color="orange" size="xs">
                        Cambiado
                      </Badge>
                    ) : null}
                  </Group>
                  {spec.hint && (
                    <Text size="xs" c="dimmed">
                      {spec.hint}
                    </Text>
                  )}
                  {row && (
                    <Text size="xs" c="dimmed">
                      Por defecto: {fallback !== undefined ? show(fallback) : AUTO.toLowerCase()}
                    </Text>
                  )}
                </Stack>
                <Group w={150} justify="flex-end">
                  <ValueInput
                    spec={spec}
                    value={row?.value}
                    fallback={fallback}
                    disabled={!unlocked}
                    onChange={(v) => set(spec, v)}
                  />
                </Group>
                <Tooltip label="Volver al valor por defecto" withArrow>
                  <ActionIcon
                    variant="subtle"
                    color="gray"
                    aria-label={`Volver al default: ${spec.label}`}
                    onClick={() => remove(spec.name)}
                    style={{ visibility: row ? 'visible' : 'hidden' }}
                  >
                    <IconArrowBackUp size={18} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            );
          })}

          {orphans.map((row) => (
            <Group key={row.key} align="center" gap="sm" wrap="wrap">
              <Stack gap={0} style={{ flex: '1 1 220px' }}>
                <Text size="sm">
                  {allSpecs.get(row.name)?.label ?? row.name}: {show(row.value)}
                </Text>
                <Text size="xs" c="dimmed">
                  {notApplies}
                </Text>
              </Stack>
              <Tooltip label="Quitar" withArrow>
                <ActionIcon
                  color="red"
                  variant="subtle"
                  aria-label={`Quitar ${row.name}`}
                  onClick={() => remove(row.name)}
                >
                  <IconTrash size={18} />
                </ActionIcon>
              </Tooltip>
            </Group>
          ))}

          {unlocked && rows.length > 0 && (
            <Button variant="subtle" color="gray" size="xs" w="fit-content" onClick={() => onChange([])}>
              Volver todo al default
            </Button>
          )}
        </Stack>
      </Collapse>
    </Stack>
  );
}

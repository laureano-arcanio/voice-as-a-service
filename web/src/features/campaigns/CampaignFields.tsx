import {
  Checkbox,
  Chip,
  Group,
  NumberInput,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import type { FieldApi, VoiceRunValues } from './campaignForm';
import { CONTACT_RESULT, RETRY_RESULTS, WEEKDAYS } from './labels';

/** Horario permitido, dias, ritmo y fechas de inicio y fin. */
export function ScheduleFields({
  api,
  rateLabel,
  rateHelp,
}: {
  api: FieldApi;
  rateLabel: string;
  rateHelp?: string;
}) {
  return (
    <Stack gap="sm">
      <Group grow align="flex-start">
        <NumberInput label="Desde (hora)" min={0} max={23} {...api.props('window_start')} />
        <NumberInput label="Hasta (hora)" min={1} max={24} {...api.props('window_end')} />
        <NumberInput
          label={rateLabel}
          description={rateHelp}
          min={1}
          max={600}
          {...api.props('rate_per_minute')}
        />
      </Group>
      <Chip.Group
        multiple
        {...(api.props('weekdays') as { value: string[]; onChange: (v: string[]) => void })}
      >
        <Stack gap={4}>
          <Text size="sm" fw={500}>
            Días permitidos
          </Text>
          <Group gap="xs">
            {WEEKDAYS.map((d) => (
              <Chip key={d.value} value={String(d.value)} size="xs">
                {d.label}
              </Chip>
            ))}
          </Group>
          <Text size="xs" c="dimmed">
            Sin ninguno marcado, todos los días. Horas y días son de la hora de Argentina.
          </Text>
        </Stack>
      </Chip.Group>
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          type="datetime-local"
          label="Inicio programado"
          description="Vacío: arranca al iniciarla."
          {...api.props('starts_at')}
        />
        <TextInput
          type="datetime-local"
          label="Termina como máximo"
          description="Vacío: sigue hasta terminar la lista."
          {...api.props('ends_at')}
        />
      </SimpleGrid>
    </Stack>
  );
}

/** Secuencial (de a una) o en paralelo con N hasta el tope del plan, y reintentos. */
export function VoiceRunFields({
  api,
  values,
  maxConcurrency,
  onMode,
}: {
  api: FieldApi;
  values: VoiceRunValues;
  maxConcurrency: number | null;
  onMode: (mode: 'sequential' | 'parallel') => void;
}) {
  const noParallel = maxConcurrency != null && maxConcurrency <= 1;
  return (
    <Stack gap="sm">
      <Group align="flex-end" gap="md">
        <Stack gap={4}>
          <Text size="sm" fw={500}>
            Modo
          </Text>
          <SegmentedControl
            aria-label="Modo"
            value={values.mode}
            onChange={(v) => onMode(v as 'sequential' | 'parallel')}
            data={[
              { value: 'sequential', label: 'De a una' },
              { value: 'parallel', label: 'En paralelo', disabled: noParallel },
            ]}
          />
        </Stack>
        {values.mode === 'parallel' && (
          <NumberInput
            label="Llamadas a la vez"
            min={2}
            max={maxConcurrency ?? undefined}
            w={160}
            {...api.props('concurrency')}
          />
        )}
      </Group>
      <Text size="xs" c="dimmed">
        {noParallel
          ? 'Tu plan permite una llamada a la vez por campaña.'
          : maxConcurrency != null
            ? `Tu plan permite hasta ${maxConcurrency} llamadas a la vez por campaña. Cuentan además en el tope de llamadas simultáneas de tu cuenta.`
            : 'Cuentan además en el tope de llamadas simultáneas de tu cuenta.'}
      </Text>
      <Group grow align="flex-start">
        <NumberInput
          label="Intentos por contacto"
          description="Con el primero incluido."
          min={1}
          max={10}
          {...api.props('max_attempts')}
        />
        <NumberInput label="Minutos entre intentos" min={1} max={10080} {...api.props('retry_minutes')} />
      </Group>
      <Checkbox.Group
        label="Se vuelve a llamar si"
        {...(api.props('retry_on') as { value: string[]; onChange: (v: string[]) => void })}
      >
        <Group mt={6} gap="md">
          {RETRY_RESULTS.map((r) => (
            <Checkbox key={r} value={r} label={CONTACT_RESULT[r].label} />
          ))}
        </Group>
      </Checkbox.Group>
    </Stack>
  );
}

/** Webhook opcional: la URL y, si se quiere, el secreto con el que se firman los avisos. */
export function WebhookFields({ api, hasSecret = false }: { api: FieldApi; hasSecret?: boolean }) {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }}>
      <TextInput
        label="URL del webhook"
        description="Opcional. Te avisamos por POST cuando termina cada contacto y la campaña."
        placeholder="https://tu-sistema.com/atentina"
        {...api.props('callback_url')}
      />
      <TextInput
        label="Secreto"
        description={
          hasSecret
            ? 'Ya hay uno guardado. Cargá otro solo si querés cambiarlo.'
            : 'Firma los avisos (HMAC-SHA256). Vacío: generamos uno y te lo mostramos una sola vez.'
        }
        {...api.props('callback_secret')}
      />
    </SimpleGrid>
  );
}

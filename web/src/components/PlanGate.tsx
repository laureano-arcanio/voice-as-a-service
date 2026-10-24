import { Button, Fieldset, Group, Paper, Stack, Text } from '@mantine/core';
import { IconLock } from '@tabler/icons-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import type { PlanFeatureKey } from '@/api/types';
import { useFeatureLock } from '@/features/billing/features';

interface PlanAlertProps {
  feature: PlanFeatureKey | PlanFeatureKey[];
  /** Lo que no incluye, para el título: "llamadas salientes". */
  what: string;
  /** Una línea más: qué sí puede hacer con su plan. */
  hint?: ReactNode;
  mb?: string;
}

/** Aviso de que el plan no incluye la función, con el camino a la pantalla Plan. Nada si la incluye. */
export function PlanAlert({ feature, what, hint, mb }: PlanAlertProps) {
  const lock = useFeatureLock(feature);
  if (!lock.locked) return null;
  return (
    <Paper withBorder px="md" py="xs" mb={mb} className="plan-alert" role="status">
      <Group gap="sm" wrap="nowrap" align="center">
        <IconLock size={18} color="var(--mantine-color-yellow-6)" style={{ flex: 'none' }} />
        <Group gap="sm" justify="space-between" align="center" style={{ flex: 1 }}>
          <Stack gap={0} style={{ flex: 1, minWidth: 220 }}>
            <Text size="sm">
              <Text span inherit fw={600}>
                Tu plan {lock.tierName} no incluye {what}.
              </Text>{' '}
              {lock.reason}
            </Text>
            {hint && (
              <Text size="xs" c="dimmed">
                {hint}
              </Text>
            )}
          </Stack>
          <Button component={Link} to="/plan" size="xs" variant="light">
            Mejorar mi plan
          </Button>
        </Group>
      </Group>
    </Paper>
  );
}

/**
 * Bloquea lo que el plan no incluye: el aviso arriba y el contenido deshabilitado y atenuado
 * (se ve qué hace, pero no se puede usar). Con el plan que la incluye, solo el contenido.
 */
export function PlanGate({ children, ...props }: PlanAlertProps & { children: ReactNode }) {
  const lock = useFeatureLock(props.feature);
  if (!lock.locked) return <>{children}</>;
  return (
    <Stack gap="md">
      <PlanAlert {...props} />
      <Fieldset
        variant="unstyled"
        disabled
        className="plan-locked"
        aria-label={`No incluido en tu plan: ${props.what}`}
      >
        {children}
      </Fieldset>
    </Stack>
  );
}

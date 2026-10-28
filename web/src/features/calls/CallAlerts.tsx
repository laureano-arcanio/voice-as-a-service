import { Alert, Anchor, Stack, Text } from '@mantine/core';
import { IconAlertTriangle, IconCircleCheck } from '@tabler/icons-react';
import { Link } from 'react-router';
import { ApiError, errorMessage } from '@/api/errors';
import type { CallStarted } from '@/api/types';
import { QUOTA_TITLES } from '@/lib/labels';

export function CallError({ error }: { error: unknown }) {
  const quota = error instanceof ApiError && error.status === 429;
  const title = quota
    ? (QUOTA_TITLES[error.code ?? ''] ?? 'Límite del plan')
    : error instanceof ApiError && error.status === 502
      ? 'No se pudo iniciar la llamada'
      : 'Error';
  return (
    <Alert color={quota ? 'yellow' : 'red'} icon={<IconAlertTriangle size={18} />} title={title}>
      <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
        {errorMessage(error)}
      </Text>
    </Alert>
  );
}

export function CallStartedAlert({ started }: { started: CallStarted }) {
  return (
    <Alert color="green" icon={<IconCircleCheck size={18} />} title="Llamada iniciada">
      <Stack gap={4}>
        <Text size="sm">El estado se actualiza solo.</Text>
        <Anchor component={Link} to={`/calls/${started.conversation_id}`} size="sm">
          Ver en vivo
        </Anchor>
      </Stack>
    </Alert>
  );
}

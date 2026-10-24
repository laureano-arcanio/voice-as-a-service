import { Anchor, Button, Grid, Group, Stack, Text } from '@mantine/core';
import { IconMicrophone } from '@tabler/icons-react';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { Agent } from '@/api/types';
import { useFeatureLock } from '@/features/billing/features';
import { VoicePicker } from '@/features/voices/VoicePicker';
import { VoicePreview } from '@/features/voices/VoicePreview';
import { BROWSER_TZ, useStartCall } from './api';
import { CallError } from './NewCallForm';

/** Una prueba del agente que todavía espera a que alguien se conecte (nadie la está usando). */
async function waitingTestCall(agentId: string): Promise<string | null> {
  const page = await unwrap(
    api.GET('/api/v1/calls', {
      params: {
        query: {
          agent_id: agentId,
          mode: 'prueba',
          status: ['pendiente', 'sonando'],
          limit: 1,
          tz: BROWSER_TZ,
        },
      },
    }),
  );
  return page.items[0]?.id ?? null;
}

/**
 * "Probar agente" por voz desde el navegador: entra a la prueba de este agente que espera conexión, o
 * crea una, y abre la pantalla de la llamada (`/calls/<id>/hablar`) en la misma pestaña (el clic deja
 * reproducir el audio).
 */
export function TestCallButton({ agent }: { agent: Agent }) {
  const navigate = useNavigate();
  const [voice, setVoice] = useState('');
  const start = useStartCall();
  const outbound = useFeatureLock('outbound_calls');
  const open = useMutation({
    mutationFn: async () => {
      const waiting = await waitingTestCall(agent.id);
      if (waiting) return waiting;
      const started = await start.mutateAsync({
        agent_id: agent.id,
        phone: null,
        from_number_id: null,
        voice: voice || null,
        loadtest: false,
      });
      return started.conversation_id;
    },
    onSuccess: (id) => void navigate(`/calls/${id}/hablar`),
  });

  return (
    <Grid gutter="md">
      <Grid.Col span={{ base: 12, md: 6 }}>
        <Stack gap="sm">
          <VoicePicker value={voice} onChange={setVoice} agentVoice={agent.voice} />
          <Group gap="sm" align="center">
            <Button
              leftSection={<IconMicrophone size={18} />}
              onClick={() => open.mutate()}
              loading={open.isPending}
            >
              Probar agente
            </Button>
            <Text size="xs" c="dimmed" style={{ flex: 1, minWidth: 200 }}>
              Hablás con el agente desde el navegador, con tu micrófono, como si fueras quien llama. No marca
              ningún teléfono ni gasta minutos.
            </Text>
          </Group>
          {!outbound.locked && (
            <Text size="xs" c="dimmed">
              Para que el agente llame a un teléfono, usá{' '}
              <Anchor component={Link} to="/outbound" inherit>
                Llamadas
              </Anchor>
              .
            </Text>
          )}
          {open.isError && <CallError error={open.error} />}
        </Stack>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 6 }}>
        <VoicePreview voice={voice || agent.voice} />
      </Grid.Col>
    </Grid>
  );
}

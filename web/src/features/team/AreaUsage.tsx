import { Anchor, Group, Stack, Text } from '@mantine/core';
import type { HandoffArea } from '@/api/types';
import { useIsClientAdmin } from '@/features/auth/useIsClientAdmin';

/** Quién deriva a esta área: agentes, números y WhatsApp. Solo lectura; los links abren en otra pestaña
 * para no perder lo que se está editando. «Números» y «WhatsApp» son de Admin. */
export function AreaUsage({ usage }: { usage: HandoffArea['used_by'] }) {
  const isAdmin = useIsClientAdmin();
  const { agents, phone_numbers: numbers, whatsapp_accounts: accounts } = usage;
  const link = (href: string, text: string) => (
    <Anchor href={href} target="_blank" rel="noopener noreferrer" size="sm">
      {text}
    </Anchor>
  );
  return (
    <Stack gap={4} data-area-usage>
      <Text size="sm" fw={600}>
        Quién deriva acá
      </Text>
      {agents.length === 0 ? (
        <Text size="xs" c="dimmed">
          Ningún agente deriva a esta área: marcala en «Derivación a personas» del agente.
        </Text>
      ) : (
        <>
          {agents.map((a) => (
            <Group key={a.id} gap={6} wrap="nowrap" align="baseline">
              {link(`/agents/${a.id}?tab=herramientas`, a.name)}
              <Text size="xs" c="dimmed">
                {a.when ? a.when : 'Usa «Qué atiende»'}
              </Text>
            </Group>
          ))}
          {numbers.length > 0 && (
            <Text size="xs" c="dimmed">
              Números:{' '}
              {numbers.map((n, i) => (
                <span key={n.id}>
                  {i > 0 && ', '}
                  {isAdmin
                    ? link('/account', `${n.e164}${n.label ? ` · ${n.label}` : ''}`)
                    : `${n.e164}${n.label ? ` · ${n.label}` : ''}`}
                  {n.answer_mode === 'team' && ' (atiende el equipo)'}
                </span>
              ))}
            </Text>
          )}
          {accounts.length > 0 && (
            <Text size="xs" c="dimmed">
              WhatsApp:{' '}
              {accounts.map((w, i) => (
                <span key={w.id}>
                  {i > 0 && ', '}
                  {isAdmin ? link('/whatsapp', w.display_phone_number) : w.display_phone_number}
                </span>
              ))}
            </Text>
          )}
        </>
      )}
    </Stack>
  );
}

import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Group,
  Image,
  List,
  Select,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useDocumentTitle } from '@mantine/hooks';
import { IconAlertCircle, IconCheck, IconPlugConnected } from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { errorMessage } from '@/api/errors';
import { QueryState } from '@/components/QueryState';
import { useCurrentUser } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { notifyError } from '@/lib/notify';
import { useAuthorizeDecision, useAuthorizeInfo } from './api';

/** Valor del selector para un admin que conecta el agente a toda la plataforma (sin cliente). */
const PLATFORM = '__platform__';

/** Lo que puede hacer un agente conectado: lo mismo que el usuario en el panel, dentro del plan. */
const CAN_DO = [
  'Ver y editar tus agentes, y probarlos por texto.',
  'Ver las llamadas y conversaciones, con sus transcripciones.',
  'Cargar contactos y armar campañas (las inicia solo si se lo confirmás).',
  'Configurar el equipo, las derivaciones y WhatsApp.',
];

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <Center mih="100vh" p="md">
      <Box w="100%" maw={460}>
        <Stack align="center" mb="lg">
          <Image src="/atentina-logo.svg" alt="Atentina" h={40} w="auto" />
        </Stack>
        {children}
      </Box>
    </Center>
  );
}

/**
 * Consentimiento OAuth del servidor MCP (/oauth/consent, la abre /oauth/authorize): un agente de IA
 * (Claude, ChatGPT, Cursor...) pide acceso a la cuenta. Al permitir o cancelar, el navegador vuelve al
 * agente con el código o el error.
 */
export function OAuthConsentPage() {
  useDocumentTitle('Conectar un agente · Atentina');
  const [search] = useSearchParams();
  const params = useMemo(() => Object.fromEntries(search.entries()), [search]);
  const info = useAuthorizeInfo(params);
  const decide = useAuthorizeDecision();
  const me = useCurrentUser();
  const clients = useClients(me.role === 'admin');
  const [clientId, setClientId] = useState<string | null>(null);
  const platform = clientId === PLATFORM;
  const [leaving, setLeaving] = useState(false);

  const submit = (approve: boolean) =>
    decide.mutate(
      {
        params,
        approve,
        client_id: me.role === 'admin' && !platform ? clientId : undefined,
        platform: me.role === 'admin' && platform ? true : undefined,
      },
      {
        onSuccess: ({ redirect_to }) => {
          setLeaving(true);
          window.location.assign(redirect_to);
        },
        onError: (e) => notifyError(e),
      },
    );

  return (
    <Shell>
      <QueryState query={info}>
        {(req) =>
          !req.valid ? (
            <Card>
              <Alert color="red" icon={<IconAlertCircle size={18} />} title="No se puede conectar el agente">
                {req.error_description ?? 'El pedido no es válido.'} Volvé a intentarlo desde la app que querés
                conectar.
              </Alert>
              {req.redirect_to && (
                <Group justify="flex-end" mt="md">
                  <Button variant="default" onClick={() => window.location.assign(req.redirect_to!)}>
                    Volver a la app
                  </Button>
                </Group>
              )}
            </Card>
          ) : (
            <Card>
              <Group gap="xs" mb="xs">
                <IconPlugConnected size={20} />
                <Title order={4}>Conectar {req.client_name}</Title>
              </Group>
              <Group gap="xs" mb="md">
                {req.verified ? (
                  <Badge color="green">Identificado por {req.client_uri ?? req.redirect_host}</Badge>
                ) : (
                  <Badge color="yellow">Registro sin verificar</Badge>
                )}
                <Text size="xs" c="dimmed">
                  Vuelve a <span className="mono">{req.redirect_host}</span>
                </Text>
              </Group>
              <Text size="sm" mb="xs">
                {req.client_name} va a poder usar tu cuenta de Atentina
                {req.client_name_tenant ? ` (${req.client_name_tenant})` : ''} como vos:
              </Text>
              <List size="sm" spacing={4} mb="md" icon={<IconCheck size={16} />}>
                {CAN_DO.map((t) => (
                  <List.Item key={t}>{t}</List.Item>
                ))}
              </List>
              <Text size="xs" c="dimmed" mb="md">
                Todo dentro de lo que incluye tu plan. Lo que el agente lee (por ejemplo, las transcripciones) pasa
                a la app que conectás. Podés desconectarlo cuando quieras desde Desarrolladores → Agentes
                conectados.
              </Text>
              {req.needs_client && (
                <Select
                  mb="md"
                  label="Cliente"
                  description="Con qué cliente va a trabajar el agente. Toda la plataforma: actúa como admin, con todas las herramientas (elige el cliente en cada una)."
                  placeholder="Elegí un cliente"
                  searchable
                  data={[
                    { value: PLATFORM, label: 'Toda la plataforma (admin)' },
                    ...(clients.data ?? []).map((c) => ({ value: c.id, label: c.name })),
                  ]}
                  value={clientId}
                  onChange={setClientId}
                />
              )}
              {platform && (
                <Alert color="yellow" icon={<IconAlertCircle size={18} />} mb="md">
                  El agente va a actuar como admin en toda la plataforma: ver y cambiar clientes, planes, números,
                  usuarios y pagos. Solo para agentes de confianza.
                </Alert>
              )}
              {decide.isError && (
                <Text c="red" size="sm" mb="sm">
                  {errorMessage(decide.error)}
                </Text>
              )}
              <Group justify="flex-end">
                <Button variant="default" disabled={decide.isPending || leaving} onClick={() => submit(false)}>
                  Cancelar
                </Button>
                <Button
                  loading={decide.isPending || leaving}
                  disabled={req.needs_client && !clientId}
                  onClick={() => submit(true)}
                >
                  Permitir acceso
                </Button>
              </Group>
            </Card>
          )
        }
      </QueryState>
    </Shell>
  );
}

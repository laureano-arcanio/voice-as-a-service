import {
  Alert,
  Anchor,
  Button,
  Code,
  Collapse,
  Group,
  List,
  Modal,
  PasswordInput,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import {
  IconAlertTriangle,
  IconCheck,
  IconChevronDown,
  IconChevronUp,
  IconInfoCircle,
} from '@tabler/icons-react';
import { useState } from 'react';
import { ApiError, errorMessage } from '@/api/errors';
import type { WaAccount } from '@/api/types';
import { CopyIcon } from '@/components/Copy';
import { useAgents } from '@/features/agents/api';
import { useConnectOwnApp } from './api';
import { WA_MANAGER_URL } from './labels';

const DIGITS = /^\d{1,32}$/;

/** Mensaje claro para los errores que el cliente puede resolver; el resto, el de la API. */
function ownAppError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'signup_mismatch') {
      return 'El número no pertenece a esa cuenta de WhatsApp Business. Revisá que el identificador del número y el de la cuenta salgan de la misma cuenta, y que el token tenga acceso a ella.';
    }
    if (e.status === 409) return 'Ese número ya está conectado en otra cuenta de Atentina.';
    if (e.status === 503) {
      return 'No podemos guardar credenciales en este momento. Avisanos y lo resolvemos.';
    }
  }
  return errorMessage(e);
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Text size="sm" fw={500}>
        {label}
      </Text>
      <Group gap={4} wrap="nowrap">
        <Code block style={{ flex: 1, wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
          {value}
        </Code>
        <CopyIcon value={value} label={`Copiar ${label.toLowerCase()}`} />
      </Group>
    </div>
  );
}

/** URL del webhook, verify token y qué hacer con ellos en la app de Meta. */
function WebhookSteps({ account }: { account: WaAccount }) {
  if (!account.webhook_url || !account.verify_token) {
    return <Text size="sm">Esta cuenta no tiene datos de webhook propios.</Text>;
  }
  return (
    <Stack gap="sm">
      <Field label="URL de devolución de llamada" value={account.webhook_url} />
      <Field label="Token de verificación" value={account.verify_token} />
      <Text size="sm">En tu app de Meta, andá a WhatsApp → Configuración → Webhook:</Text>
      <List type="ordered" size="sm" spacing={4}>
        <List.Item>Pegá la URL de devolución de llamada y el token de verificación.</List.Item>
        <List.Item>Tocá "Verificar y guardar".</List.Item>
        <List.Item>
          En los campos del webhook, suscribite a <Code>messages</Code>.
        </List.Item>
      </List>
    </Stack>
  );
}

/** Datos del webhook de una cuenta con app propia (la URL y el token no cambian al actualizar el token). */
export function WebhookDataModal({ account, onClose }: { account: WaAccount; onClose: () => void }) {
  return (
    <Modal opened onClose={onClose} title={`Datos del webhook de ${account.display_phone_number}`} size="lg">
      <Stack>
        <WebhookSteps account={account} />
        <Group justify="flex-end">
          <Button onClick={onClose}>Listo</Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/** Lo que el cliente hace en Meta antes de cargar los datos. */
function Guide() {
  return (
    <Stack gap="xs">
      <List type="ordered" size="sm" spacing="xs">
        <List.Item>
          En{' '}
          <Anchor
            href="https://developers.facebook.com/apps"
            target="_blank"
            rel="noopener noreferrer"
            inherit
          >
            developers.facebook.com
          </Anchor>
          , creá una app de tipo Business y agregale el producto WhatsApp, asociada a tu cuenta de WhatsApp
          Business.
        </List.Item>
        <List.Item>Pasá la app a modo Live. Meta te pide la URL de tu política de privacidad.</List.Item>
        <List.Item>
          En{' '}
          <Anchor
            href="https://business.facebook.com/settings/system-users"
            target="_blank"
            rel="noopener noreferrer"
            inherit
          >
            business.facebook.com
          </Anchor>{' '}
          → Configuración del negocio → Usuarios del sistema, creá un usuario de sistema, asignale la app y tu
          cuenta de WhatsApp, y generá un token permanente con los permisos{' '}
          <Code>whatsapp_business_messaging</Code> y <Code>whatsapp_business_management</Code>.
        </List.Item>
        <List.Item>
          Copiá de la app el identificador del número de teléfono y el de la cuenta de WhatsApp Business
          (WhatsApp → Configuración de la API), y la clave secreta de la app (Configuración de la app →
          Básica).
        </List.Item>
      </List>
      <Alert color="yellow" icon={<IconInfoCircle size={18} />} p="xs">
        <Text size="sm">
          Un número que hoy usás en la app WhatsApp Business del celular no se puede conectar así sin dejar
          esa app. Mantener las dos a la vez pide la coexistencia, que todavía no está disponible.
        </Text>
      </Alert>
    </Stack>
  );
}

/** Paso final: webhook para pegar en Meta, o el motivo si quedó pendiente. */
function Done({
  account,
  updated,
  onRetry,
  onClose,
}: {
  account: WaAccount;
  updated: boolean;
  onRetry: () => void;
  onClose: () => void;
}) {
  return (
    <Stack>
      {account.status === 'connected' ? (
        <Alert
          color="green"
          icon={<IconCheck size={18} />}
          title={updated ? 'Datos actualizados' : 'Número conectado'}
        >
          {account.display_phone_number}
          {account.name ? ` (${account.name})` : ''} lo atiende {account.agent_name ?? 'el agente elegido'}.
          {updated ? '' : ' Falta un paso en Meta: configurar el webhook.'}
        </Alert>
      ) : (
        <Alert color="yellow" icon={<IconAlertTriangle size={18} />} title="Guardado, falta un paso">
          <Text size="sm">
            {account.display_phone_number} quedó pendiente:{' '}
            {account.status_reason ?? 'Meta no confirmó el número'}. Podés reintentar con los mismos datos o
            con un token nuevo.
          </Text>
        </Alert>
      )}
      <WebhookSteps account={account} />
      <Text size="sm" c="dimmed">
        Meta le cobra los mensajes a tu cuenta de WhatsApp Business: cargá el medio de pago en{' '}
        <Anchor href={WA_MANAGER_URL} target="_blank" rel="noopener noreferrer" inherit>
          WhatsApp Manager
        </Anchor>
        .
      </Text>
      <Group justify="flex-end">
        {account.status !== 'connected' && (
          <Button variant="default" onClick={onRetry}>
            Reintentar
          </Button>
        )}
        <Button onClick={onClose}>Listo</Button>
      </Group>
    </Stack>
  );
}

/**
 * Conectar un número con la app de Meta del cliente: guía de lo que se hace en Meta, formulario
 * (agente, IDs, token y app secret) y, al guardar, la URL del webhook y el token para pegar en la app.
 * Con `account` actualiza el token y el secret de un número ya conectado.
 */
export function OwnAppModal({ account, onClose }: { account?: WaAccount; onClose: () => void }) {
  const update = !!account;
  const connect = useConnectOwnApp();
  const [guide, setGuide] = useState(!update);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<WaAccount | null>(null);
  const agents = useAgents(account?.client_id, false);
  const form = useForm({
    initialValues: {
      agent_id: account?.agent_id ?? '',
      phone_number_id: account?.phone_number_id ?? '',
      waba_id: account?.waba_id ?? '',
      access_token: '',
      app_secret: '',
    },
    validate: {
      agent_id: (v) => (v ? null : 'Elegí el agente'),
      phone_number_id: (v) => (DIGITS.test(v.trim()) ? null : 'Solo dígitos (el identificador del número)'),
      waba_id: (v) => (DIGITS.test(v.trim()) ? null : 'Solo dígitos (el identificador de la cuenta)'),
      access_token: (v) => (v.trim() ? null : 'Pegá el token permanente'),
      app_secret: (v) => (v.trim() ? null : 'Pegá la clave secreta de la app'),
    },
  });
  const agentData = (agents.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  // El agente actual puede estar archivado: se sigue mostrando.
  if (account && !agentData.some((o) => o.value === account.agent_id)) {
    agentData.push({ value: account.agent_id, label: `${account.agent_name ?? 'Agente'} (archivado)` });
  }

  const submit = form.onSubmit((v) => {
    setError(null);
    connect.mutate(
      {
        agent_id: v.agent_id,
        phone_number_id: v.phone_number_id.trim(),
        waba_id: v.waba_id.trim(),
        access_token: v.access_token.trim(),
        app_secret: v.app_secret.trim(),
      },
      { onSuccess: (a) => setDone(a), onError: (e) => setError(ownAppError(e)) },
    );
  });

  return (
    <Modal
      opened
      onClose={connect.isPending ? () => {} : onClose}
      title={update ? `Actualizar token de ${account.display_phone_number}` : 'Conectar con mi app de Meta'}
      size="lg"
    >
      {done ? (
        <Done
          account={done}
          updated={update}
          onRetry={() => {
            setDone(null);
            form.setFieldValue('access_token', '');
            form.setFieldValue('app_secret', '');
          }}
          onClose={onClose}
        />
      ) : (
        <form onSubmit={submit}>
          <Stack>
            <Text size="sm">
              {update
                ? 'Cargá el token y la clave secreta nuevos. La URL del webhook y el token de verificación no cambian.'
                : 'Conectás tu número con tu propia app de Meta: los mensajes llegan a Atentina por un webhook que vos configurás, y Meta te cobra a tu cuenta de WhatsApp Business.'}
            </Text>
            <Anchor component="button" type="button" size="sm" onClick={() => setGuide((v) => !v)} ta="left">
              <Group gap={4}>
                {guide ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
                {guide ? 'Ocultar la guía paso a paso' : 'Ver la guía paso a paso'}
              </Group>
            </Anchor>
            <Collapse in={guide}>
              <Guide />
            </Collapse>
            <Select
              label="Agente que responde"
              placeholder="Elegí el agente"
              data={agentData}
              searchable
              autoComplete="off"
              nothingFoundMessage="Sin agentes"
              {...form.getInputProps('agent_id')}
            />
            <Group grow align="flex-start">
              <TextInput
                label="Identificador del número"
                description="Phone number ID, no el teléfono."
                classNames={{ input: 'mono' }}
                inputMode="numeric"
                disabled={update}
                autoComplete="off"
                {...form.getInputProps('phone_number_id')}
              />
              <TextInput
                label="Identificador de la cuenta"
                description="WhatsApp Business Account ID."
                classNames={{ input: 'mono' }}
                inputMode="numeric"
                autoComplete="off"
                {...form.getInputProps('waba_id')}
              />
            </Group>
            <PasswordInput
              label="Token permanente"
              description="Del usuario de sistema. Se guarda cifrado y no se vuelve a mostrar."
              autoComplete="off"
              {...form.getInputProps('access_token')}
            />
            <PasswordInput
              label="Clave secreta de la app"
              description="App Secret: Configuración de la app → Básica. Firma los webhooks."
              autoComplete="off"
              {...form.getInputProps('app_secret')}
            />
            {error && (
              <Alert color="red" icon={<IconAlertTriangle size={18} />} title="No se conectó">
                <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
                  {error}
                </Text>
              </Alert>
            )}
            <Group justify="flex-end">
              <Button variant="default" onClick={onClose} disabled={connect.isPending}>
                Cancelar
              </Button>
              <Button type="submit" loading={connect.isPending}>
                {update ? 'Guardar' : 'Conectar'}
              </Button>
            </Group>
          </Stack>
        </form>
      )}
    </Modal>
  );
}

import {
  Alert,
  Anchor,
  Button,
  Collapse,
  Group,
  Modal,
  PasswordInput,
  Select,
  Stack,
  Text,
} from '@mantine/core';
import { IconAlertTriangle, IconBrandWhatsapp, IconCheck, IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';
import { errorMessage } from '@/api/errors';
import type { WaAccount, WaConfig } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { useCurrentUser } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { useWaSignup } from './api';
import { WA_MANAGER_URL } from './labels';
import { SignupAbort, useEmbeddedSignup } from './useEmbeddedSignup';

type Phase = 'form' | 'popup' | 'saving';

const PIN = /^\d{6}$/;

/** Resultado del alta: conectado o pendiente, y el aviso del medio de pago. */
function SignupDone({ account, onClose }: { account: WaAccount; onClose: () => void }) {
  return (
    <Stack>
      {account.status === 'connected' ? (
        <Alert color="green" icon={<IconCheck size={18} />} title="Número conectado">
          {account.display_phone_number}
          {account.name ? ` (${account.name})` : ''} ya recibe mensajes; lo atiende{' '}
          {account.agent_name ?? 'el agente elegido'}.
        </Alert>
      ) : (
        <Alert color="yellow" icon={<IconAlertTriangle size={18} />} title="Conectado, falta un paso">
          <Text size="sm">
            {account.display_phone_number} quedó pendiente:{' '}
            {account.status_reason ?? 'falta registrar el número'}.
          </Text>
          <Text size="sm" mt={4}>
            Usá "Reintentar registro" en el menú del número. Si el número ya tenía verificación en dos pasos,
            cargá ese PIN.
          </Text>
        </Alert>
      )}
      {account.source === 'coexistence' && (
        <Text size="sm" c="dimmed">
          El número sigue funcionando en la app de WhatsApp Business. Meta da 24 h para sincronizar contactos
          e historial desde la app.
        </Text>
      )}
      <Alert color="blue" icon={<IconInfoCircle size={18} />} title="Cargá el medio de pago">
        Meta le cobra los mensajes a tu cuenta de WhatsApp Business: sin medio de pago no termina el alta.
        Cargalo en{' '}
        <Anchor href={WA_MANAGER_URL} target="_blank" rel="noopener noreferrer">
          WhatsApp Manager
        </Anchor>
        .
      </Alert>
      <Group justify="flex-end">
        <Button onClick={onClose}>Listo</Button>
      </Group>
    </Stack>
  );
}

/**
 * Conectar un número propio por Embedded Signup: elegir el agente, abrir el popup de Meta,
 * y mandar a la API el código (vence a los 30 s) con los IDs del número.
 */
export function SignupModal({ config, onClose }: { config: WaConfig; onClose: () => void }) {
  const me = useCurrentUser();
  const isAdmin = me.role === 'admin';
  const clients = useClients(isAdmin);
  const [clientId, setClientId] = useState<string | null>(isAdmin ? null : me.client_id);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [pin, setPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  const [phase, setPhase] = useState<Phase>('form');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<WaAccount | null>(null);
  const agents = useAgents(clientId ?? undefined, false, !!clientId);
  const signup = useWaSignup();
  const fb = useEmbeddedSignup(config);
  const insecure = typeof window !== 'undefined' && window.location.protocol !== 'https:';
  const pinError = pin && !PIN.test(pin) ? 'Son 6 dígitos' : null;
  const busy = phase !== 'form';

  const start = () => {
    if (!agentId || !clientId || pinError) return;
    setError(null);
    setPhase('popup');
    // launch() abre el popup en este mismo click (si no, el navegador lo bloquea).
    fb.launch().then(
      (r) => {
        setPhase('saving');
        signup.mutate(
          {
            code: r.code,
            event: r.event,
            waba_id: r.waba_id,
            phone_number_id: r.phone_number_id,
            business_id: r.business_id,
            agent_id: agentId,
            client_id: isAdmin ? clientId : null,
            pin: pin || null,
          },
          {
            onSuccess: (a) => setDone(a),
            onError: (e) => {
              setError(errorMessage(e));
              setPhase('form');
            },
          },
        );
      },
      (e: unknown) => {
        setPhase('form');
        if (e instanceof SignupAbort && e.kind === 'cancel') setError(e.message);
        else setError(e instanceof Error ? e.message : 'No se pudo completar el alta.');
      },
    );
  };

  return (
    <Modal
      opened
      onClose={busy ? () => {} : onClose}
      title="Conectar WhatsApp"
      size="lg"
      closeOnClickOutside={!busy}
    >
      {done ? (
        <SignupDone account={done} onClose={onClose} />
      ) : (
        <Stack>
          <Text size="sm">
            Se abre una ventana de Meta: entrás con tu cuenta de Facebook, elegís o creás tu portafolio y tu
            cuenta de WhatsApp Business, y cargás y verificás el número (SMS o llamada). Al terminar, el
            número queda atendido por el agente que elijas acá.
          </Text>
          {insecure && (
            <Alert color="yellow" icon={<IconAlertTriangle size={18} />}>
              Meta solo permite el alta desde un dominio con HTTPS declarado en la app (app.atentina.com.ar).
              Desde esta dirección la ventana va a fallar.
            </Alert>
          )}
          {isAdmin && (
            <Select
              label="Cliente"
              data={(clients.data ?? []).filter((c) => c.active).map((c) => ({ value: c.id, label: c.name }))}
              value={clientId}
              onChange={(v) => {
                setClientId(v);
                setAgentId(null);
              }}
              searchable
              disabled={busy}
            />
          )}
          <Select
            label="Agente que responde"
            placeholder={clientId ? 'Elegí el agente' : 'Elegí primero el cliente'}
            data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
            value={agentId}
            onChange={setAgentId}
            disabled={!clientId || busy}
            searchable
            nothingFoundMessage="Sin agentes"
          />
          <Anchor component="button" type="button" size="sm" onClick={() => setShowPin((v) => !v)} ta="left">
            {showPin ? 'Ocultar opciones' : 'El número ya tiene verificación en dos pasos'}
          </Anchor>
          <Collapse in={showPin}>
            <PasswordInput
              label="PIN de verificación en dos pasos (opcional)"
              description="Solo si el número ya tenía un PIN. Vacío: se genera uno y se guarda cifrado."
              value={pin}
              onChange={(e) => setPin(e.currentTarget.value.trim())}
              error={pinError}
              maxLength={6}
              inputMode="numeric"
              autoComplete="off"
              disabled={busy}
            />
          </Collapse>
          {fb.loadError && (
            <Alert color="red" icon={<IconAlertTriangle size={18} />}>
              {fb.loadError}
            </Alert>
          )}
          {error && (
            <Alert color="red" icon={<IconAlertTriangle size={18} />} title="No se conectó">
              <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
                {error}
              </Text>
            </Alert>
          )}
          {phase === 'popup' && (
            <Text size="sm" c="dimmed">
              Seguí los pasos en la ventana de Meta…
            </Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose} disabled={busy}>
              Cancelar
            </Button>
            <Button
              color="green"
              leftSection={<IconBrandWhatsapp size={18} />}
              onClick={start}
              loading={busy || (!fb.ready && !fb.loadError)}
              disabled={!agentId || !fb.ready || !!pinError}
            >
              Conectar WhatsApp
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}

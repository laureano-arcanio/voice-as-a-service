import {
  Alert,
  Anchor,
  Button,
  Collapse,
  Group,
  Modal,
  PasswordInput,
  Stack,
  Text,
} from '@mantine/core';
import { IconAlertTriangle, IconBrandWhatsapp, IconCheck, IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';
import { errorMessage } from '@/api/errors';
import type { WaAccount, WaConfig } from '@/api/types';
import { ModalSelect } from '@/components/ModalDropdown';
import { useAgents } from '@/features/agents/api';
import { useWaSignup } from './api';
import { WA_ATTENDANCE, WA_MANAGER_URL, waStatusReason } from './labels';
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
            {waStatusReason(account.status_reason) ?? 'falta registrar el número'}.
          </Text>
          <Text size="sm" mt={4}>
            Usá "Reintentar registro" en el menú del número. Si el número ya tenía verificación en dos pasos,
            cargá ese PIN.
          </Text>
        </Alert>
      )}
      {(account.source === 'coexistence' || account.on_biz_app) && (
        <Text size="sm" c="dimmed">
          El número sigue funcionando en tu app de WhatsApp Business y en el teléfono. Abrí la app en el teléfono
          al menos cada 14 días: si no, Meta desconecta el número.
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
  const [agentId, setAgentId] = useState<string | null>(null);
  const [attendance, setAttendance] = useState<'agent' | 'owner'>('agent');
  const [pin, setPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  const [phase, setPhase] = useState<Phase>('form');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<WaAccount | null>(null);
  const agents = useAgents(undefined, false);
  const signup = useWaSignup();
  const fb = useEmbeddedSignup(config);
  const insecure = typeof window !== 'undefined' && window.location.protocol !== 'https:';
  const pinError = pin && !PIN.test(pin) ? 'Son 6 dígitos' : null;
  const busy = phase !== 'form';

  const start = () => {
    if (!agentId || pinError) return;
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
            client_id: null,
            attendance,
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
            Se abre una ventana de Meta: entrás con tu cuenta de Facebook, elegís tu portafolio y tu cuenta de
            WhatsApp Business. Podés conectar un número nuevo o el que ya usás en la app de WhatsApp Business: ese
            sigue en el teléfono (coexistencia). Después elegís quién atiende los mensajes.
          </Text>
          <Text size="sm" c="dimmed">
            Si el número también es personal, elegí "Dueño" o conectá un segundo número para el agente: en modo
            Agente no conviene responder desde la app.
          </Text>
          {insecure && (
            <Alert color="yellow" icon={<IconAlertTriangle size={18} />}>
              Meta solo permite el alta desde un dominio con HTTPS declarado en la app (app.atentina.com.ar).
              Desde esta dirección la ventana va a fallar.
            </Alert>
          )}
          <ModalSelect
            label="Quién responde"
            description="Agente: contesta la IA. Dueño: lo atendés vos desde la app o el teléfono y la IA no contesta."
            data={[
              { value: 'agent', label: WA_ATTENDANCE.agent.label },
              { value: 'owner', label: WA_ATTENDANCE.owner.label },
            ]}
            value={attendance}
            onChange={(v) => v && setAttendance(v as 'agent' | 'owner')}
            allowDeselect={false}
            disabled={busy}
          />
          <ModalSelect
            label="Agente que responde"
            description="Responde cuando el modo es Agente."
            placeholder="Elegí el agente"
            data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
            value={agentId}
            onChange={setAgentId}
            autoComplete="off"
            disabled={busy}
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
              autoComplete="one-time-code"
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

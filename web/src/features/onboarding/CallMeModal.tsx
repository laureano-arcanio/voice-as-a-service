import { Alert, Button, Group, Modal, PinInput, Stack, Text, TextInput } from '@mantine/core';
import { IconBrandWhatsapp, IconDeviceMobile, IconPhoneCall } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { errorMessage } from '@/api/errors';
import type { Agent, Onboarding } from '@/api/types';
import { voiceName } from '@/features/voices/names';
import { useCallMe, useSendPhoneCode, useVerifyPhone } from './api';
import { trialLeft } from './catalog';

/**
 * "Llamame a mi celular": verifica el celular con un código por WhatsApp (una vez) y el agente llama
 * (POST /onboarding/call-me). Las de prueba no gastan minutos del plan.
 */
export function CallMeModal({
  agent,
  status,
  opened,
  onClose,
}: {
  agent: Agent;
  status: Onboarding;
  opened: boolean;
  onClose: () => void;
}) {
  const [phone, setPhone] = useState(status.phone ?? '');
  const [challenge, setChallenge] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [calling, setCalling] = useState<string | null>(null);
  const send = useSendPhoneCode();
  const verify = useVerifyPhone();
  const callMe = useCallMe();
  const name = voiceName(agent.voice ?? 'sofia');
  const left = trialLeft(status);
  const verified = status.phone_verified;

  const close = () => {
    setChallenge(null);
    setCode('');
    setCalling(null);
    send.reset();
    verify.reset();
    callMe.reset();
    onClose();
  };

  const call = () =>
    callMe.mutate(agent.id, {
      onSuccess: (started) => setCalling(started.conversation_id),
    });

  let body;
  if (!status.verify_available) {
    body = (
      <Alert color="yellow" icon={<IconDeviceMobile size={18} />}>
        La llamada a tu celular se habilita en unos días. Mientras tanto, hablale desde el navegador.
      </Alert>
    );
  } else if (calling) {
    body = (
      <Stack align="center" ta="center" gap="sm">
        <IconPhoneCall size={40} color="var(--mantine-color-blue-6)" />
        <Text fw={600}>
          {name} te está llamando al <span className="mono">{status.phone}</span>
        </Text>
        <Text size="sm" c="dimmed">
          Atendé y hablale como si fueras un cliente. Cuando termine, la conversación queda en Conversaciones.
        </Text>
        <Group>
          <Button variant="default" onClick={close}>
            Cerrar
          </Button>
          <Button component={Link} to={`/calls/${calling}`} onClick={close}>
            Ver la conversación
          </Button>
        </Group>
      </Stack>
    );
  } else if (verified) {
    body = (
      <Stack gap="sm">
        <Text size="sm">
          {name} te llama al <b className="mono">{status.phone}</b>.{' '}
          {left > 0
            ? `Te quedan ${left} ${left === 1 ? 'llamada' : 'llamadas'} de prueba, de hasta ${Math.round(status.trial.seconds_max / 60)} minutos en total.`
            : 'Ya usaste las llamadas de prueba.'}
        </Text>
        {callMe.error && <Alert color="red">{errorMessage(callMe.error)}</Alert>}
        <Group justify="flex-end">
          <Button variant="default" onClick={close}>
            Cancelar
          </Button>
          <Button leftSection={<IconPhoneCall size={18} />} disabled={left === 0} loading={callMe.isPending} onClick={call}>
            Llamame ahora
          </Button>
        </Group>
      </Stack>
    );
  } else if (!challenge) {
    body = (
      <Stack gap="sm">
        <Text size="sm">Primero confirmamos que el celular es tuyo: te mandamos un código por WhatsApp.</Text>
        <TextInput
          label="Tu celular"
          placeholder="11 5555-1234"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.currentTarget.value)}
          error={send.error ? errorMessage(send.error) : undefined}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={close}>
            Cancelar
          </Button>
          <Button
            leftSection={<IconBrandWhatsapp size={18} />}
            loading={send.isPending}
            disabled={phone.trim().length < 6}
            onClick={() => send.mutate(phone, { onSuccess: (r) => setChallenge(r.challenge) })}
          >
            Mandar el código
          </Button>
        </Group>
      </Stack>
    );
  } else {
    body = (
      <Stack gap="sm">
        <Text size="sm">Escribí el código de 6 números que te llegó por WhatsApp.</Text>
        <PinInput length={6} type="number" oneTimeCode value={code} onChange={setCode} aria-label="Código" />
        {verify.error && <Alert color="red">{errorMessage(verify.error)}</Alert>}
        <Group justify="space-between">
          <Button variant="subtle" size="compact-sm" onClick={() => setChallenge(null)}>
            Cambiar el número
          </Button>
          <Button
            loading={verify.isPending}
            disabled={code.length !== 6}
            onClick={() => verify.mutate({ challenge, code }, { onSuccess: () => setCode('') })}
          >
            Verificar
          </Button>
        </Group>
      </Stack>
    );
  }

  return (
    <Modal opened={opened} onClose={close} title="Que tu agente te llame" centered>
      {body}
    </Modal>
  );
}

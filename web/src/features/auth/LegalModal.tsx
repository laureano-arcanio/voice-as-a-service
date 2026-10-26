import { Anchor, Button, Checkbox, Group, Modal, Stack, Text } from '@mantine/core';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError } from '@/api/errors';
import { notifyError } from '@/lib/notify';
import { meKey, useAcceptLegal, useMe } from './api';

/** Condiciones o política de privacidad vigentes que el usuario no aceptó (invitados por un admin, cuentas de antes
 * de la casilla del registro o una versión nueva): no se cierra hasta aceptarlas (docs/TERMINOS_PLAN.md). */
export function LegalModal() {
  const { data: me } = useMe();
  const accept = useAcceptLegal();
  const qc = useQueryClient();
  const [checked, setChecked] = useState(false);
  const pending = me?.legal_pending ?? [];
  if (!pending.length) return null;

  const terms = pending.find((d) => d.document === 'terms');
  const privacy = pending.find((d) => d.document === 'privacy');
  const updated = !!me && !me.welcome_pending;
  const submit = () =>
    accept.mutate(
      // Solo las pendientes: la que ya aceptó va vacía.
      { terms_version: terms?.version ?? '', privacy_version: privacy?.version ?? '' },
      {
        onError: (e) => {
          if (e instanceof ApiError && e.code === 'terms_outdated')
            void qc.invalidateQueries({ queryKey: meKey });
          notifyError(e, 'No se pudo registrar la aceptación');
        },
      },
    );

  return (
    <Modal
      opened
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      size="lg"
      title={updated ? 'Actualizamos nuestras condiciones' : 'Condiciones del servicio'}
    >
      <Stack gap="md">
        <Text size="sm">
          {updated
            ? 'Para seguir usando el panel, leé y aceptá las versiones nuevas. Si no estás de acuerdo, podés darte de baja sin costo.'
            : 'Antes de empezar, leé y aceptá las condiciones del servicio y la política de privacidad.'}
        </Text>
        <Stack gap={4}>
          {pending.map((d) => (
            <Anchor key={d.document} href={d.url} target="_blank" rel="noopener noreferrer" size="sm">
              {d.title} (versión {d.version})
            </Anchor>
          ))}
        </Stack>
        <Text size="xs" c="dimmed">
          En resumen: el agente es una IA y puede equivocarse, así que lo probás y lo revisás; vos respondés
          por tus datos y tus contactos; los planes pagos se renuevan cada mes, te das de baja cuando quieras
          y tenés 10 días para arrepentirte.
        </Text>
        <Checkbox
          checked={checked}
          onChange={(e) => setChecked(e.currentTarget.checked)}
          label="Leí y acepto las condiciones del servicio y la política de privacidad."
        />
        <Group justify="space-between" gap="sm">
          <Anchor
            href="https://atentina.com.ar/baja"
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
            c="dimmed"
          >
            Darme de baja
          </Anchor>
          <Button onClick={submit} disabled={!checked} loading={accept.isPending}>
            Aceptar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

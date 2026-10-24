import { Anchor, Button, Card, Group, List, Modal, SimpleGrid, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconBrandYoutube } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useMe, useWelcomeSeen } from './api';

// Links a YouTube (sin embeber: la CSP del panel no deja iframes ni imágenes de YouTube).
const VIDEOS = [
  { title: 'Qué es Atentina', detail: 'Presentación', url: 'https://www.youtube.com/watch?v=J7lRGDyu9js' },
  {
    title: 'Cómo crear y probar agentes',
    detail: 'Tutorial corto',
    url: 'https://www.youtube.com/shorts/azBM8bJl_Xw',
  },
];

/** Bienvenida la primera vez que entra un usuario de cliente: qué es la plataforma, por dónde
 * empezar y los videos. Al cerrarla (de cualquier forma) no vuelve a aparecer. */
export function WelcomeModal() {
  const { data: me } = useMe();
  const seen = useWelcomeSeen();
  const navigate = useNavigate();
  const [closed, setClosed] = useState(false);

  const close = (to?: string) => {
    setClosed(true);
    seen.mutate();
    if (to) void navigate(to);
  };

  return (
    <Modal
      opened={!!me?.welcome_pending && !closed}
      onClose={() => close()}
      size="lg"
      title="Te damos la bienvenida a Atentina"
    >
      <Stack gap="md">
        <Text size="sm">
          Atentina atiende el teléfono y el WhatsApp de tu negocio con un agente de IA que habla como una persona.
          Desde este panel lo armás, lo probás y ves cada conversación.
        </Text>
        <List size="sm" spacing={6} type="ordered">
          <List.Item>
            <b>Creá tu agente</b> en Agentes › Mis agentes: qué hace, cómo habla y qué datos pide.
          </List.Item>
          <List.Item>
            <b>Probalo</b> en Probar agentes: le hablás desde el navegador, antes de que atienda a nadie.
          </List.Item>
          <List.Item>
            <b>Conectalo</b> a tu línea, a WhatsApp o a un link para llamar, según tu plan.
          </List.Item>
          <List.Item>
            <b>Mirá los resultados</b> en Conversaciones: transcripción, datos y resultado de cada una.
          </List.Item>
        </List>
        <Text className="label">Videos</Text>
        <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="sm">
          {VIDEOS.map((v) => (
            <Card key={v.url} component="a" href={v.url} target="_blank" rel="noopener noreferrer" padding="sm">
              <Group gap="sm" wrap="nowrap">
                <ThemeIcon color="red" variant="light" size="lg">
                  <IconBrandYoutube size={20} />
                </ThemeIcon>
                <Stack gap={0}>
                  <Anchor component="span" size="sm" fw={600}>
                    {v.title}
                  </Anchor>
                  <Text size="xs" c="dimmed">
                    {v.detail} · YouTube
                  </Text>
                </Stack>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={() => close()}>
            Explorar el panel
          </Button>
          <Button onClick={() => close('/agents')}>Crear mi agente</Button>
        </Group>
      </Stack>
    </Modal>
  );
}

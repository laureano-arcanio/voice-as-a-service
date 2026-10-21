import { Button, Card, Center, Image, PasswordInput, Stack, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { setApiKey } from './api';

/** Pide la CRM_API_KEY una vez; queda en el navegador. Un 401 la borra y vuelve aca. */
export function KeyGate({ onSaved }: { onSaved: () => void }) {
  const [value, setValue] = useState('');
  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cleanKey(value)) return;
    onSaved();
    setApiKey(cleanKey(value));
  };
  return (
    <Center mih="100vh" p="md" bg="var(--app-canvas)">
      <Card withBorder w="100%" maw={400}>
        <form onSubmit={save}>
          <Stack>
            <Image
              src="/atentina-logo.svg"
              alt="Atentina"
              h={28}
              w="auto"
              fit="contain"
              style={{ alignSelf: 'flex-start' }}
            />
            <Title order={4}>CRM de ventas</Title>
            <Text size="sm" c="dimmed">
              Pegá la key del CRM (<span className="mono">CRM_API_KEY</span> del .env). Queda guardada en este
              navegador.
            </Text>
            <PasswordInput
              label="Key"
              value={value}
              onChange={(e) => setValue(e.currentTarget.value)}
              autoFocus
              data-autofocus
            />
            <Button type="submit" disabled={!value.trim()}>
              Entrar
            </Button>
          </Stack>
        </form>
      </Card>
    </Center>
  );
}

// Acepta la key pegada con el nombre de la variable o con espacios ("CRM_API_KEY=...").
function cleanKey(raw: string): string {
  return raw.trim().split(/\s+/)[0].replace(/^CRM_API_KEY=/, '');
}

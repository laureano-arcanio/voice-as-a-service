import { Anchor, Card, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import type { Client, User } from '@/api/types';
import { QueryState } from '@/components/QueryState';
import { useIndustries } from '@/features/onboarding/api';
import { PhoneVerified } from '@/features/users/PhoneVerified';
import { useUsers } from '@/features/users/api';
import { formatDate } from '@/lib/format';

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600} component="div">
        {children || '–'}
      </Text>
    </Stack>
  );
}

/** El usuario que se registró: el primero que se creó para el cliente. */
function firstUser(users: User[]): User | undefined {
  return [...users].sort((a, b) => a.created_at.localeCompare(b.created_at))[0];
}

/** Lo que dejó el cliente al registrarse: empresa, sus datos de contacto y, si los dio, rubro y sitio. */
export function RegistrationCard({ client }: { client: Client }) {
  const users = useUsers(client.id);
  const industries = useIndustries(Boolean(client.industry));
  const industry = industries.data?.find((i) => i.id === client.industry)?.label ?? client.industry;

  return (
    <Card>
      <Title order={4} mb="md">
        Datos de registro
      </Title>
      <QueryState query={users}>
        {(list) => {
          const user = firstUser(list);
          return (
            <Stack gap="sm">
              <Row label="Empresa">{client.name}</Row>
              <Row label="Nombre">{user?.name}</Row>
              <Row label="Email">{user?.email}</Row>
              <Row label="Celular">
                {user?.phone && <PhoneVerified phone={user.phone} verifiedAt={user.phone_verified_at ?? null} />}
              </Row>
              <Row label="Rubro">{industry}</Row>
              <Row label="Sitio web">
                {client.website && (
                  <Anchor href={client.website} target="_blank" rel="noreferrer" size="sm">
                    {client.website}
                  </Anchor>
                )}
              </Row>
              <Row label="Alta">
                {formatDate(client.created_at)} ·{' '}
                {client.created_via === 'signup' ? 'registro desde la landing' : 'creado por un admin'}
              </Row>
            </Stack>
          );
        }}
      </QueryState>
    </Card>
  );
}

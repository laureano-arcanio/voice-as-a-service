import { Card } from '@mantine/core';
import { PageHeader } from '@/components/PageHeader';
import { UsersTable } from './UsersTable';

export function UsersPage() {
  return (
    <>
      <PageHeader
        title="Usuarios"
        description="Administradores (ven y gestionan todo) y usuarios de cada cliente (ven solo lo suyo)."
      />
      <Card>
        <UsersTable />
      </Card>
    </>
  );
}

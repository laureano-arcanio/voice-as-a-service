import { PageHeader } from '@/components/PageHeader';
import { MessagesTable } from '../components/MessagesTable';

export function MessagesPage() {
  return (
    <>
      <PageHeader title="Mensajes" description="Todo lo enviado, en cola, en borrador y recibido." />
      <MessagesTable />
    </>
  );
}

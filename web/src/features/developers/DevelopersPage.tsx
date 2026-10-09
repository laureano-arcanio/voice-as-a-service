import { PageHeader } from '@/components/PageHeader';
import { useCurrentUser } from '@/features/auth/api';
import { ApiAccess } from './ApiAccess';

/** API del cliente: API keys con su alcance, consumo contra el plan y como conectarse a LLM, STT y TTS. */
export function DevelopersPage() {
  const me = useCurrentUser();
  if (!me.client_id) return null;
  return (
    <>
      <PageHeader
        title="API"
        description="Creá API keys para llamar a nuestro LLM, transcripción y síntesis de voz desde tus sistemas."
      />
      <ApiAccess clientId={me.client_id} />
    </>
  );
}

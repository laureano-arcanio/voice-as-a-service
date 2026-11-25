import { ActionIcon, Button, Tooltip } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { confirmAction } from '@/components/confirm';
import { useIsClientAdmin } from '@/features/auth/useIsClientAdmin';
import { notifyError, notifyInfo, notifySuccess } from '@/lib/notify';
import { canReanalyze, useReanalyze } from './api';

/** Volver a correr el análisis (solo Admin del cliente): re-extrae los datos y el resumen con el prompt
 * vigente del agente, pisando los actuales. Se oculta solo si no aplica o si el usuario no puede. */
export function ReanalyzeButton({
  conversationId,
  hasAnalysis,
  callStatus,
  compact = false,
}: {
  conversationId: string;
  hasAnalysis?: boolean | null;
  callStatus?: string | null;
  compact?: boolean;
}) {
  const isClientAdmin = useIsClientAdmin();
  const reanalyze = useReanalyze(conversationId);
  if (!isClientAdmin || !canReanalyze({ has_analysis: hasAnalysis, status: callStatus })) return null;

  const run = async () => {
    const ok = await confirmAction({
      title: 'Volver a correr el análisis',
      message:
        'Se extraen de nuevo los datos y el resumen con el prompt vigente del agente y se pisan los actuales: lo que esta corrida no obtenga queda vacío.',
      confirmLabel: 'Volver a correr',
    });
    if (!ok) return;
    reanalyze.mutate(undefined, {
      onSuccess: (r) =>
        r.pending
          ? notifyInfo('El análisis sigue corriendo en el fondo; los datos aparecen al terminar.')
          : notifySuccess('Análisis vuelto a correr.'),
      onError: (e) => notifyError(e, 'No se pudo volver a correr el análisis'),
    });
  };

  return compact ? (
    <Tooltip label="Volver a correr el análisis">
      <ActionIcon
        variant="subtle"
        loading={reanalyze.isPending}
        onClick={() => void run()}
        aria-label="Volver a correr el análisis"
      >
        <IconRefresh size={16} />
      </ActionIcon>
    </Tooltip>
  ) : (
    <Button
      variant="default"
      leftSection={<IconRefresh size={18} />}
      onClick={() => void run()}
      loading={reanalyze.isPending}
    >
      Volver a correr el análisis
    </Button>
  );
}

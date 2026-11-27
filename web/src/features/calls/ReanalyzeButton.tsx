import { ActionIcon, Button, Menu } from '@mantine/core';
import { IconChevronDown, IconRefresh } from '@tabler/icons-react';
import { confirmAction } from '@/components/confirm';
import { useIsClientAdmin } from '@/features/auth/useIsClientAdmin';
import { notifyError, notifyInfo, notifySuccess } from '@/lib/notify';
import { canReanalyze, useReanalyze, type ReanalyzeVersion } from './api';

/** Volver a correr el análisis (solo Admin del cliente): re-extrae los datos y el resumen, pisando los
 * actuales, con la última versión del agente o con la de la conversación. Se oculta solo si no aplica o si el
 * usuario no puede. */
export function ReanalyzeButton({
  conversationId,
  agentVersion,
  hasAnalysis,
  callStatus,
  analysisStatus,
  compact = false,
}: {
  conversationId: string;
  /** La versión con la que corrió la conversación (vN en el menú). */
  agentVersion?: number | null;
  hasAnalysis?: boolean | null;
  callStatus?: string | null;
  /** `pending` o `running`: la extracción final está corriendo y el botón no aplica. */
  analysisStatus?: string | null;
  compact?: boolean;
}) {
  const isClientAdmin = useIsClientAdmin();
  const reanalyze = useReanalyze(conversationId);
  if (!isClientAdmin || !canReanalyze({ has_analysis: hasAnalysis, status: callStatus, analysis_status: analysisStatus }))
    return null;

  const versionLabel = agentVersion != null ? ` (v${agentVersion})` : '';
  const run = async (version: ReanalyzeVersion) => {
    const conversation = version === 'conversation';
    const ok = await confirmAction({
      title: 'Volver a correr el análisis',
      message: conversation
        ? `Se extraen de nuevo los datos y el resumen con el análisis de la versión de esta conversación${versionLabel} y se pisan los actuales: lo que esta corrida no obtenga queda vacío.`
        : 'Se extraen de nuevo los datos y el resumen con el análisis de la última versión del agente y se pisan los actuales: lo que esta corrida no obtenga queda vacío.',
      confirmLabel: 'Volver a correr',
    });
    if (!ok) return;
    reanalyze.mutate(version, {
      onSuccess: (r) =>
        r.pending
          ? notifyInfo('El análisis sigue corriendo en el fondo; los datos aparecen al terminar.')
          : notifySuccess(
              conversation
                ? 'Análisis vuelto a correr con la versión de la conversación.'
                : 'Análisis vuelto a correr con la última versión.',
            ),
      onError: (e) => notifyError(e, 'No se pudo volver a correr el análisis'),
    });
  };

  return (
    <Menu position={compact ? 'bottom-end' : 'bottom-start'} withinPortal>
      <Menu.Target>
        {compact ? (
          <ActionIcon
            variant="subtle"
            loading={reanalyze.isPending}
            title="Volver a correr el análisis"
            aria-label="Volver a correr el análisis"
          >
            <IconRefresh size={16} />
          </ActionIcon>
        ) : (
          <Button
            variant="default"
            leftSection={<IconRefresh size={18} />}
            rightSection={<IconChevronDown size={16} />}
            loading={reanalyze.isPending}
          >
            Volver a correr el análisis
          </Button>
        )}
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={() => void run('latest')}>La última versión del agente</Menu.Item>
        <Menu.Item onClick={() => void run('conversation')}>
          La versión de esta conversación{versionLabel}
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}

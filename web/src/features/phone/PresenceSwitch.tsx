import { Switch, Tooltip } from '@mantine/core';
import { usePresence } from './context';

/** Disponible para atender en el panel: mientras está prendido, las entrantes del equipo suenan acá. */
export function PresenceSwitch({ size = 'sm' }: { size?: 'xs' | 'sm' | 'md' }) {
  const { available, setAvailable, disabledReason } = usePresence();
  return (
    <Tooltip
      label={disabledReason ?? 'Con el panel abierto, te suenan acá las llamadas de tus números.'}
      withArrow
      multiline
      w={260}
    >
      <Switch
        size={size}
        label="Disponible"
        color="green"
        checked={available}
        disabled={!!disabledReason}
        onChange={(e) => setAvailable(e.currentTarget.checked)}
      />
    </Tooltip>
  );
}

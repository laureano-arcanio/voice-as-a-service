import { ActionIcon, CopyButton, Tooltip } from '@mantine/core';
import { IconCheck, IconCopy } from '@tabler/icons-react';

export function CopyIcon({ value, label = 'Copiar' }: { value: string; label?: string }) {
  return (
    <CopyButton value={value} timeout={2000}>
      {({ copied, copy }) => (
        <Tooltip label={copied ? 'Copiado' : label} withArrow>
          <ActionIcon variant="subtle" color={copied ? 'green' : 'gray'} onClick={copy} aria-label={label}>
            {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
          </ActionIcon>
        </Tooltip>
      )}
    </CopyButton>
  );
}

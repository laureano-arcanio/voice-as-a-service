import { Alert, Code } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

export function SipNotice() {
  return (
    <Alert color="blue" icon={<IconInfoCircle size={18} />} mb="md">
      Después de cargar o borrar números, correr <Code>make livekit-sip</Code> en el server para que LiveKit
      los acepte.
    </Alert>
  );
}

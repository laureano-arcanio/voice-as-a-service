import { Badge, Group, Text, Tooltip } from '@mantine/core';
import { formatDateTime } from '@/lib/format';

/** Un celular de usuario y si lo verificó por WhatsApp. */
export function PhoneVerified({ phone, verifiedAt }: { phone: string; verifiedAt: string | null }) {
  return (
    <Group component="span" gap={6} wrap="nowrap" style={{ display: 'inline-flex' }}>
      <Text span inherit className="mono">
        {phone}
      </Text>
      {verifiedAt ? (
        <Tooltip label={`Verificado el ${formatDateTime(verifiedAt)}`}>
          <Badge color="green">Verificado</Badge>
        </Tooltip>
      ) : (
        <Badge color="gray">Sin verificar</Badge>
      )}
    </Group>
  );
}

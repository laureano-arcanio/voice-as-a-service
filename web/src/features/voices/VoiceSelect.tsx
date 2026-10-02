import {
  Avatar,
  Badge,
  Button,
  Group,
  Radio,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { useVoices } from './api';
import { GENDER_LABEL, voiceName } from './names';
import { VoicePreview } from './VoicePreview';

const VISIBLE = 9;

/**
 * Voz de un agente, como en la landing: tarjetas con la inicial, el nombre y el genero, y al
 * lado la prueba con la voz elegida. '' = ninguna (usa la predeterminada del sistema).
 */
export function VoiceSelect({
  value,
  onChange,
  previewText,
}: {
  value: string;
  onChange: (voice: string) => void;
  /** Texto de partida de la prueba (ej. la apertura del agente). */
  previewText?: string;
}) {
  const voices = useVoices();
  const [gender, setGender] = useState('');
  const [all, setAll] = useState(false);

  const items = voices.data ?? [];
  const count = (g: string) => items.filter((v) => v.genero === g).length;
  const filtered = gender ? items.filter((v) => v.genero === gender) : items;
  let shown = all ? filtered : filtered.slice(0, VISIBLE);
  // La elegida siempre a la vista.
  const current = items.find((v) => v.nombre === value);
  if (current && !shown.includes(current) && filtered.includes(current))
    shown = [current, ...shown.slice(0, VISIBLE - 1)];

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
      <Stack gap="sm">
        <SegmentedControl
          w="fit-content"
          size="xs"
          data={[
            { value: '', label: `Todas (${items.length})` },
            { value: 'mujer', label: `Mujeres (${count('mujer')})` },
            { value: 'hombre', label: `Hombres (${count('hombre')})` },
          ]}
          value={gender}
          onChange={setGender}
        />
        <Radio.Group value={value} onChange={onChange} aria-label="Voz">
          <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="xs">
            {shown.map((v) => {
              const checked = v.nombre === value;
              return (
                <Radio.Card key={v.nombre} value={v.nombre} p="xs">
                  <Group gap="sm" wrap="nowrap">
                    <Avatar
                      size={36}
                      radius="xl"
                      color={checked ? 'blue' : 'gray'}
                      variant={checked ? 'filled' : 'light'}
                    >
                      {voiceName(v.nombre).charAt(0)}
                    </Avatar>
                    <Stack gap={2} style={{ minWidth: 0 }}>
                      <Text size="sm" fw={600} truncate>
                        {voiceName(v.nombre)}
                      </Text>
                      <Badge color="gray">{GENDER_LABEL[v.genero] ?? v.genero}</Badge>
                    </Stack>
                  </Group>
                </Radio.Card>
              );
            })}
          </SimpleGrid>
        </Radio.Group>
        {filtered.length > VISIBLE && (
          <Button variant="subtle" size="compact-sm" w="fit-content" onClick={() => setAll((x) => !x)}>
            {all ? 'Ver menos' : `Ver todas (${filtered.length})`}
          </Button>
        )}
      </Stack>
      <div className="def-item">
        <Stack gap="sm">
          <Group justify="space-between" align="baseline" wrap="wrap">
            <Title order={3}>{value ? voiceName(value) : 'Sin voz elegida'}</Title>
            {current ? (
              <Badge color="gray">{GENDER_LABEL[current.genero] ?? current.genero}</Badge>
            ) : (
              !value && (
                <Text size="xs" c="dimmed">
                  Usa la predeterminada del sistema
                </Text>
              )
            )}
          </Group>
          <VoicePreview voice={value || null} initialText={previewText} compact />
        </Stack>
      </div>
    </SimpleGrid>
  );
}

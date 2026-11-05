import { Button, Card, FileButton, Group, Select, Stack, Text, Textarea, Title } from '@mantine/core';
import { IconUpload } from '@tabler/icons-react';
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { useSupportReadOnly } from '@/features/billing/features';
import { useVoices } from '@/features/voices/api';
import { voiceName } from '@/features/voices/names';
import { formatNumber } from '@/lib/format';
import { notifyError } from '@/lib/notify';
import { useCreateSpeech, useStudioItems, useStudioQuota, isActive } from './api';
import { History, MinutesLeft, SupportNotice } from './parts';

const MAX_CHARS = 20_000;
const DEFAULT_CHARS_PER_SECOND = 16;

export function SpeechPage() {
  const readOnly = useSupportReadOnly();
  const voices = useVoices();
  const create = useCreateSpeech();
  const items = useStudioItems('tts');
  const quota = useStudioQuota('tts', !!items.data?.items.some(isActive));
  const [text, setText] = useState('');
  const [picked, setPicked] = useState<string | null>(null);
  const voice = picked ?? voices.data?.[0]?.nombre ?? null;
  const speed = voices.data?.find((v) => v.nombre === voice)?.car_s ?? DEFAULT_CHARS_PER_SECOND;
  const minutes = text.trim().length / speed / 60;

  const loadFile = async (file: File | null) => {
    if (!file) return;
    const content = await file.text();
    if (content.length > MAX_CHARS) {
      notifyError(
        new Error(`El archivo tiene más de ${formatNumber(MAX_CHARS, 0)} caracteres.`),
        'No se pudo cargar',
      );
      return;
    }
    setText(content);
  };

  const submit = () => {
    if (!voice) return;
    create.mutate(
      { text, voice },
      { onSuccess: () => setText(''), onError: (e) => notifyError(e, 'No se pudo sintetizar') },
    );
  };

  return (
    <>
      <PageHeader title="Texto a voz" description="Pegá o subí un texto, elegí la voz y descargá el audio." />
      <Stack gap="md">
        <Card>
          <Stack gap="sm">
            <Textarea
              aria-label="Texto"
              placeholder="Escribí o pegá tu texto acá"
              autosize
              minRows={6}
              maxRows={16}
              maxLength={MAX_CHARS}
              value={text}
              onChange={(e) => setText(e.currentTarget.value)}
              disabled={readOnly}
            />
            <Group justify="space-between" align="flex-end" gap="sm">
              <Group gap="sm" align="flex-end">
                <Select
                  label="Voz"
                  searchable
                  w={220}
                  data={(voices.data ?? []).map((v) => ({ value: v.nombre, label: voiceName(v.nombre) }))}
                  value={voice}
                  onChange={setPicked}
                  allowDeselect={false}
                  disabled={readOnly}
                />
                <FileButton onChange={(f) => void loadFile(f)} accept=".txt,text/plain" disabled={readOnly}>
                  {(props) => (
                    <Button {...props} variant="default" leftSection={<IconUpload size={16} />}>
                      Subir .txt
                    </Button>
                  )}
                </FileButton>
              </Group>
              <Button
                onClick={submit}
                loading={create.isPending}
                disabled={readOnly || !quota.included || !text.trim() || !voice}
              >
                Sintetizar
              </Button>
            </Group>
            <Text size="xs" c="dimmed">
              {text.trim()
                ? `${formatNumber(text.trim().length, 0)} caracteres, unos ${formatNumber(Math.max(minutes, 0.1))} minutos de audio.`
                : `Hasta ${formatNumber(MAX_CHARS, 0)} caracteres.`}
            </Text>
            {readOnly ? <SupportNotice /> : <MinutesLeft kind="tts" {...quota} />}
          </Stack>
        </Card>
        <Card>
          <Stack gap="sm">
            <Title order={4}>Tus audios</Title>
            <History kind="tts" readOnly={readOnly} />
          </Stack>
        </Card>
      </Stack>
    </>
  );
}

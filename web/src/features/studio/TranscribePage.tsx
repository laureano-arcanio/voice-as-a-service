import { Button, Card, FileButton, Group, Stack, Text, Title } from '@mantine/core';
import { IconUpload } from '@tabler/icons-react';
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { useSupportReadOnly } from '@/features/billing/features';
import { notifyError } from '@/lib/notify';
import { isActive, useCreateTranscription, useStudioItems, useStudioQuota } from './api';
import { History, MinutesLeft, SupportNotice } from './parts';

const ACCEPT =
  '.mp3,.mpeg,.mpga,.wav,.ogg,.oga,.opus,.flac,.m4a,.mp4,.aac,.webm,.mkv,.aiff,.aif,.amr,.wma,.3gp';
const MAX_MB = 95;

export function TranscribePage() {
  const readOnly = useSupportReadOnly();
  const create = useCreateTranscription();
  const items = useStudioItems('stt');
  const quota = useStudioQuota('stt', !!items.data?.items.some(isActive));
  const [file, setFile] = useState<File | null>(null);

  const submit = () => {
    if (!file) return;
    if (file.size > MAX_MB * 1024 * 1024) {
      notifyError(new Error(`El archivo supera los ${MAX_MB} MB.`), 'No se pudo subir');
      return;
    }
    create.mutate(file, {
      onSuccess: () => setFile(null),
      onError: (e) => notifyError(e, 'No se pudo transcribir'),
    });
  };

  return (
    <>
      <PageHeader
        title="Transcribir"
        description="Subí un audio y te devolvemos el texto para copiar o descargar."
      />
      <Stack gap="md">
        <Card>
          <Stack gap="sm">
            <Group justify="space-between" gap="sm">
              <Group gap="sm">
                <FileButton onChange={setFile} accept={ACCEPT} disabled={readOnly}>
                  {(props) => (
                    <Button {...props} variant="default" leftSection={<IconUpload size={16} />}>
                      Elegir archivo
                    </Button>
                  )}
                </FileButton>
                <Text size="sm" c={file ? undefined : 'dimmed'}>
                  {file?.name ?? `MP3, WAV, OGG, M4A y otros, hasta ${MAX_MB} MB`}
                </Text>
              </Group>
              <Button
                onClick={submit}
                loading={create.isPending}
                disabled={readOnly || !quota.included || !file}
              >
                Transcribir
              </Button>
            </Group>
            {readOnly ? <SupportNotice /> : <MinutesLeft kind="stt" {...quota} />}
          </Stack>
        </Card>
        <Card>
          <Stack gap="sm">
            <Title order={4}>Tus transcripciones</Title>
            <History kind="stt" readOnly={readOnly} />
          </Stack>
        </Card>
      </Stack>
    </>
  );
}

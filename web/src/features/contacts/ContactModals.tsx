import {
  Alert,
  Badge,
  Button,
  FileInput,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconFileUpload, IconInfoCircle } from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import type { Contact, ContactRejected, ContactsUpsert } from '@/api/types';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useImportContacts, useUpdateContact, useUpsertContact } from './api';
import { previewCsv, ROLE_LABEL } from './csv';

const MAX_CSV_BYTES = 900_000;
const PREVIEW_ROWS = 5;

/** Lee un archivo .csv y entrega el texto (hasta ~900 KB). */
export function CsvFileInput({ onText }: { onText: (text: string) => void }) {
  return (
    <FileInput
      label="O subí un archivo"
      placeholder="contactos.csv"
      accept=".csv,text/csv,text/plain"
      leftSection={<IconFileUpload size={16} />}
      clearable
      onChange={(file) => {
        if (!file) return;
        if (file.size > MAX_CSV_BYTES) {
          notifyError(new Error('El archivo pasa de 900 KB: dividilo en partes.'));
          return;
        }
        void file.text().then(onText);
      }}
    />
  );
}

/** Filas que no entraron, con la fila del CSV y el motivo. */
export function RejectedTable({ rows }: { rows: ContactRejected[] }) {
  return (
    <Table.ScrollContainer minWidth={420} mah={260}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Fila</Table.Th>
            <Table.Th>Teléfono</Table.Th>
            <Table.Th>Motivo</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((s, i) => (
            <Table.Tr key={i}>
              <Table.Td className="mono">{s.line ?? '–'}</Table.Td>
              <Table.Td className="mono">{s.phone || '–'}</Table.Td>
              <Table.Td>{s.reason}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

/** Que entendió la API del CSV: columnas con su destino y las primeras filas. */
export function CsvPreviewTable({ text }: { text: string }) {
  const preview = useMemo(() => previewCsv(text), [text]);
  if (!preview) return null;
  if (preview.error)
    return (
      <Alert color="red" icon={<IconInfoCircle size={18} />}>
        {preview.error}
      </Alert>
    );
  return (
    <Stack gap="xs">
      <Text size="sm">
        <b>{preview.rows.length}</b> {preview.rows.length === 1 ? 'fila' : 'filas'} para cargar. Se arman
        estos campos:
      </Text>
      <Table.ScrollContainer minWidth={420}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              {preview.columns.map((c, i) => (
                <Table.Th key={i}>
                  <Text className="mono" size="xs" fw={600}>
                    {c.header}
                  </Text>
                  <Badge color={c.role === 'phone' ? 'blue' : 'gray'} mt={2}>
                    {ROLE_LABEL[c.role]}
                  </Badge>
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {preview.rows.slice(0, PREVIEW_ROWS).map((r, i) => (
              <Table.Tr key={i}>
                {preview.columns.map((_, j) => (
                  <Table.Td key={j} className="mono">
                    {r[j] ?? ''}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      {preview.rows.length > PREVIEW_ROWS && (
        <Text size="xs" c="dimmed">
          Y {preview.rows.length - PREVIEW_ROWS} más.
        </Text>
      )}
    </Stack>
  );
}

/** Resultado de una carga a la agenda: creados, actualizados, archivados e invalidos. */
export function UpsertResult({ result }: { result: ContactsUpsert }) {
  return (
    <Stack gap="xs">
      <Text size="sm">
        <b>{result.created}</b> {result.created === 1 ? 'contacto nuevo' : 'contactos nuevos'},{' '}
        <b>{result.updated}</b> {result.updated === 1 ? 'actualizado' : 'actualizados'}.
      </Text>
      {result.archived > 0 && (
        <Alert color="yellow" icon={<IconInfoCircle size={18} />}>
          {result.archived} {result.archived === 1 ? 'ya estaba archivado' : 'ya estaban archivados'}: se
          actualizaron sus datos, pero siguen archivados. Desarchivalos desde la lista si querés usarlos.
        </Alert>
      )}
      {result.invalid.length > 0 && (
        <>
          <Text size="sm">{result.invalid.length} quedaron afuera:</Text>
          <RejectedTable rows={result.invalid} />
        </>
      )}
    </Stack>
  );
}

export function ImportContactsModal({ onClose }: { onClose: () => void }) {
  const imp = useImportContacts();
  const [csv, setCsv] = useState('');
  const [result, setResult] = useState<ContactsUpsert | null>(null);
  const preview = useMemo(() => previewCsv(csv), [csv]);
  const canImport = !!preview && !preview.error && preview.rows.length > 0;

  return (
    <Modal opened onClose={onClose} title="Importar contactos" size="lg">
      {result ? (
        <Stack>
          <UpsertResult result={result} />
          <Group justify="flex-end">
            <Button onClick={onClose}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          <Textarea
            label="Contactos (CSV)"
            description="Una fila por contacto, con encabezado. Va una columna de teléfono (telefono, celular, phone, whatsapp); nombre, email, id_externo y notas son opcionales; las demás columnas se ignoran. Quien ya está en la agenda se actualiza."
            placeholder={'telefono,nombre,email\n351 555-1234,Ana Pérez,ana@empresa.com'}
            autosize
            minRows={5}
            maxRows={12}
            classNames={{ input: 'mono' }}
            value={csv}
            onChange={(e) => setCsv(e.currentTarget.value)}
            data-autofocus
          />
          <CsvFileInput onText={setCsv} />
          <CsvPreviewTable text={csv} />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              disabled={!canImport}
              loading={imp.isPending}
              onClick={() =>
                imp.mutate(
                  { csv },
                  { onSuccess: setResult, onError: (e) => notifyError(e, 'No se pudo importar') },
                )
              }
            >
              Importar
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}

/** Alta y edicion de un contacto. El telefono solo se carga al crear: otro telefono es otro contacto. */
export function ContactModal({ contact, onClose }: { contact: Contact | null; onClose: () => void }) {
  const create = useUpsertContact();
  const update = useUpdateContact(contact?.id ?? '');
  const form = useForm({
    initialValues: {
      phone: contact?.phone ?? '',
      name: contact?.name ?? '',
      email: contact?.email ?? '',
      external_id: contact?.external_id ?? '',
      notes: contact?.notes ?? '',
    },
    validate: {
      phone: (v) => (contact || v.trim() ? null : 'Requerido'),
    },
  });

  const submit = form.onSubmit((v) => {
    const common = {
      name: v.name.trim() || null,
      email: v.email.trim() || null,
      external_id: v.external_id.trim() || null,
      notes: v.notes.trim() || null,
    };
    if (contact)
      update.mutate(common, {
        onSuccess: () => {
          notifySuccess('Contacto guardado.');
          onClose();
        },
        onError: (e) => notifyError(e, 'No se pudo guardar'),
      });
    else
      create.mutate({ phone: v.phone.trim(), ...common }, {
        onSuccess: (r) => {
          notifySuccess(
            r.created
              ? 'Contacto agregado.'
              : 'Ese teléfono ya estaba en la agenda: se actualizaron sus datos.',
          );
          if (r.archived)
            notifyError(
              new Error('Está archivado: desarchivalo desde la lista para usarlo.'),
              'Contacto archivado',
            );
          onClose();
        },
        onError: (e) => notifyError(e, 'No se pudo agregar'),
      });
  });

  return (
    <Modal opened onClose={onClose} title={contact ? 'Editar contacto' : 'Nuevo contacto'} size="lg">
      <form onSubmit={submit}>
        <Stack>
          <TextInput
            label="Teléfono"
            description={contact ? 'No se cambia: otro teléfono es otro contacto.' : undefined}
            placeholder="351 555-1234"
            disabled={!!contact}
            classNames={{ input: 'mono' }}
            data-autofocus={!contact || undefined}
            {...form.getInputProps('phone')}
          />
          <Group grow align="flex-start">
            <TextInput label="Nombre" placeholder="Ana Pérez" {...form.getInputProps('name')} />
            <TextInput label="Email" placeholder="ana@empresa.com" {...form.getInputProps('email')} />
          </Group>
          <TextInput
            label="ID externo"
            description="El id de este contacto en tu sistema."
            {...form.getInputProps('external_id')}
          />
          <Textarea
            label="Notas"
            placeholder="Ej.: prefiere que lo llamen por la tarde"
            autosize
            minRows={3}
            maxRows={8}
            maxLength={2000}
            {...form.getInputProps('notes')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending || update.isPending}>
              {contact ? 'Guardar cambios' : 'Agregar contacto'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

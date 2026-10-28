import {
  Checkbox,
  Group,
  Pagination,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { Dash } from '@/components/Badges';
import { QueryState } from '@/components/QueryState';
import { CONTACTS_PAGE, useContacts } from '@/features/contacts/api';
import { CsvFileInput, CsvPreviewTable } from '@/features/contacts/ContactModals';
import { type Recipients, recipientsCount, recipientsSummary } from './recipients';

function ContactChooser({
  clientId,
  selected,
  onChange,
}: {
  clientId?: string;
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  const [search, setSearch] = useState('');
  const [q] = useDebouncedValue(search.trim(), 300);
  const [page, setPage] = useState(1);
  const contacts = useContacts({
    clientId,
    q,
    archived: 'false',
    offset: (page - 1) * CONTACTS_PAGE,
  });
  const chosen = new Set(selected);
  const toggle = (id: string) =>
    onChange(chosen.has(id) ? selected.filter((x) => x !== id) : [...selected, id]);

  return (
    <Stack gap="xs">
      <TextInput
        aria-label="Buscar contactos"
        placeholder="Buscar por nombre, teléfono o email"
        leftSection={<IconSearch size={16} />}
        value={search}
        onChange={(e) => {
          setSearch(e.currentTarget.value);
          setPage(1);
        }}
      />
      <QueryState query={contacts}>
        {(data) =>
          data.items.length === 0 ? (
            <Text size="sm" c="dimmed" ta="center" py="md">
              {q ? 'No hay contactos con esa búsqueda.' : 'La agenda no tiene contactos activos.'}
            </Text>
          ) : (
            <>
              <Table.ScrollContainer minWidth={420} mah={260}>
                <Table>
                  <Table.Tbody>
                    {data.items.map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td w={36}>
                          <Checkbox
                            aria-label={`Elegir ${c.name || c.phone}`}
                            checked={chosen.has(c.id)}
                            onChange={() => toggle(c.id)}
                          />
                        </Table.Td>
                        <Table.Td className="mono">{c.phone}</Table.Td>
                        <Table.Td>{c.name ?? <Dash />}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
              {data.total > CONTACTS_PAGE && (
                <Group justify="flex-end">
                  <Pagination
                    size="sm"
                    total={Math.ceil(data.total / CONTACTS_PAGE)}
                    value={page}
                    onChange={setPage}
                  />
                </Group>
              )}
            </>
          )
        }
      </QueryState>
    </Stack>
  );
}

export function RecipientsPicker({
  clientId,
  value,
  onChange,
}: {
  clientId?: string;
  value: Recipients;
  onChange: (next: Recipients) => void;
}) {
  const n = recipientsCount(value);
  const badge = (count: number) => (count ? ` (${count})` : '');

  return (
    <Stack gap="xs">
      <Text size="sm" fw={500}>
        Destinatarios
      </Text>
      <Tabs defaultValue="contacts" keepMounted={false}>
        <Tabs.List mb="sm">
          <Tabs.Tab value="contacts">Elegir contactos{badge(n.ids)}</Tabs.Tab>
          <Tabs.Tab value="csv">CSV{badge(n.rows)}</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="contacts">
          <ContactChooser
            clientId={clientId}
            selected={value.contactIds}
            onChange={(contactIds) => onChange({ ...value, contactIds })}
          />
        </Tabs.Panel>
        <Tabs.Panel value="csv">
          <Stack gap="xs">
            <Textarea
              aria-label="Contactos (CSV)"
              description="Con encabezado: telefono (obligatorio), nombre, email y notas. Quienes no estén en la agenda se agregan."
              placeholder={'telefono,nombre,email\n351 555-1234,Ana Pérez,ana@empresa.com'}
              autosize
              minRows={4}
              maxRows={10}
              classNames={{ input: 'mono' }}
              value={value.csv}
              onChange={(e) => onChange({ ...value, csv: e.currentTarget.value })}
            />
            <CsvFileInput onText={(csv) => onChange({ ...value, csv })} />
            <CsvPreviewTable text={value.csv} />
          </Stack>
        </Tabs.Panel>
      </Tabs>
      <Text size="xs" c="dimmed">
        {recipientsSummary(value)}
      </Text>
    </Stack>
  );
}

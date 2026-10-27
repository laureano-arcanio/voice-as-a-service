import { Button } from '@mantine/core';
import { IconDownload } from '@tabler/icons-react';
import { downloadCsv, toCsv, type CsvColumn } from '@/lib/csv';

/** "Descargar CSV" con los datos que muestra la tabla o el grafico. Sin filas, deshabilitado. */
export function CsvButton<T>({
  filename,
  rows,
  columns,
}: {
  filename: string;
  rows: readonly T[];
  columns: readonly CsvColumn<T>[];
}) {
  return (
    <Button
      variant="subtle"
      size="compact-sm"
      leftSection={<IconDownload size={16} />}
      disabled={!rows.length}
      onClick={() => downloadCsv(filename, toCsv(rows, columns))}
    >
      Descargar CSV
    </Button>
  );
}

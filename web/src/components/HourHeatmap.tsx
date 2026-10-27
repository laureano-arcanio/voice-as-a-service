import { Box, Group, Table, Text, Tooltip, VisuallyHidden } from '@mantine/core';

const WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const SHORT = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const HOURS = Array.from({ length: 24 }, (_, h) => h);

export interface HeatValue {
  /** 0 = lunes. */
  weekday: number;
  hour: number;
  value: number;
  /** Texto del tooltip; por defecto "<valor> <unidad>". */
  detail?: string;
}

/** Intensidad del color de la marca: 0 queda en superficie 2; el maximo, el primario lleno. */
function shade(value: number, max: number): string | undefined {
  if (!value || !max) return undefined;
  const pct = Math.round(15 + (85 * value) / max);
  return `color-mix(in srgb, var(--mantine-color-blue-6) ${pct}%, var(--mantine-color-white))`;
}

/**
 * Mapa de calor dia de la semana x hora (hora local). Es una tabla: cada celda lleva su valor en
 * `aria-label`, asi se lee con lector de pantalla; el color es solo apoyo.
 */
export function HourHeatmap({
  cells,
  caption,
  unit,
  format = (v) => String(v),
}: {
  cells: readonly HeatValue[];
  /** Que se cuenta, para el lector de pantalla: "Llamadas por día y hora". */
  caption: string;
  /** Unidad del tooltip: "llamadas". */
  unit: string;
  format?: (v: number) => string;
}) {
  const grid = new Map(cells.map((c) => [`${c.weekday}-${c.hour}`, c]));
  const max = Math.max(0, ...cells.map((c) => c.value));
  return (
    <Box>
      <Table.ScrollContainer minWidth={640} type="native">
        <Table className="hour-heatmap" withRowBorders={false} highlightOnHover={false} layout="fixed">
          <VisuallyHidden component="caption">{caption}</VisuallyHidden>
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={44}>
                <VisuallyHidden>Día</VisuallyHidden>
              </Table.Th>
              {HOURS.map((h) => (
                <Table.Th key={h} ta="center" aria-label={`${h} h`}>
                  {h % 3 === 0 ? h : ''}
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {SHORT.map((d, wd) => (
              <Table.Tr key={d}>
                <Table.Th scope="row" aria-label={WEEKDAYS[wd]}>
                  {d}
                </Table.Th>
                {HOURS.map((h) => {
                  const c = grid.get(`${wd}-${h}`);
                  const v = c?.value ?? 0;
                  const text = `${WEEKDAYS[wd]} ${h} h: ${c?.detail ?? `${format(v)} ${unit}`}`;
                  return (
                    <Tooltip key={h} label={text} openDelay={100}>
                      <Table.Td
                        aria-label={text}
                        className="hour-heatmap-cell"
                        style={{ background: shade(v, max) }}
                      />
                    </Tooltip>
                  );
                })}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      <Group gap={6} justify="flex-end" mt={6} aria-hidden>
        <Text size="xs" c="dimmed">
          Menos
        </Text>
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <span
            key={f}
            className="hour-heatmap-cell hour-heatmap-key"
            style={{ background: shade(f * (max || 1), max || 1) }}
          />
        ))}
        <Text size="xs" c="dimmed">
          Más
        </Text>
      </Group>
    </Box>
  );
}

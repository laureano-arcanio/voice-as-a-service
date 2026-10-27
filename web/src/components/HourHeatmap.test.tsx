import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/render';
import { HourHeatmap } from './HourHeatmap';

describe('HourHeatmap', () => {
  it('una celda por día y hora, con su valor para el lector de pantalla', async () => {
    renderWithProviders(
      <HourHeatmap
        caption="Llamadas por día y hora"
        unit="llamadas"
        cells={[
          { weekday: 0, hour: 9, value: 4 },
          { weekday: 6, hour: 23, value: 1 },
        ]}
      />,
    );
    expect(await screen.findByRole('table', { name: 'Llamadas por día y hora' })).toBeInTheDocument();
    expect(screen.getAllByRole('cell')).toHaveLength(7 * 24);
    expect(screen.getByLabelText('Lunes 9 h: 4 llamadas')).toBeInTheDocument();
    expect(screen.getByLabelText('Domingo 23 h: 1 llamadas')).toBeInTheDocument();
    expect(screen.getByLabelText('Martes 0 h: 0 llamadas')).toBeInTheDocument();
  });
});

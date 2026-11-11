import { Select, Stack, Textarea } from '@mantine/core';
import type { ReactNode } from 'react';

/** Lo que pide un destino al elegirlo: un selector (área, persona, agente) o un texto (el mensaje). */
export type NoAnswerDetail =
  | {
      type: 'select';
      label: string;
      description?: string;
      placeholder?: string;
      options: { value: string; label: string }[];
      value: string | null;
      onChange: (id: string | null) => void;
      nothingFound?: string;
      error?: ReactNode;
    }
  | {
      type: 'text';
      label: string;
      description?: string;
      placeholder?: string;
      value: string;
      onChange: (text: string) => void;
      maxLength?: number;
      error?: ReactNode;
    };

/** Un destino de «si nadie atiende». Cada pantalla pasa los que admite: el control no conoce ninguno. */
export interface NoAnswerDestination {
  value: string;
  label: string;
  /** No se puede elegir (ej. no hay personas para elegir). */
  disabled?: boolean;
  /** Lo que se pide al elegirlo. Sin detail, el destino no pide nada. */
  detail?: NoAnswerDetail;
  /** Se llama al dejar este destino por otro: la pantalla borra su detalle. */
  clear?: () => void;
}

/**
 * «Si nadie atiende»: un destino de la lista y su detalle. Lo usan las pantallas donde una llamada puede quedar
 * sin atender (áreas de derivación, números en modo equipo); cada una pasa sus destinos y guarda el valor.
 */
export function NoAnswerField({
  label = 'Si nadie atiende',
  description,
  value,
  onChange,
  destinations,
}: {
  label?: string;
  description?: string;
  /** El `value` del destino elegido. */
  value: string;
  onChange: (value: string) => void;
  destinations: NoAnswerDestination[];
}) {
  const current = destinations.find((d) => d.value === value);
  const detail = current?.detail;
  return (
    <Stack gap="xs">
      <Select
        label={label}
        description={description}
        data={destinations.map((d) => ({ value: d.value, label: d.label, disabled: d.disabled }))}
        allowDeselect={false}
        value={current ? value : null}
        onChange={(next) => {
          if (!next || next === value) return;
          current?.clear?.();
          onChange(next);
        }}
      />
      {detail?.type === 'select' && (
        <Select
          label={detail.label}
          description={detail.description}
          placeholder={detail.placeholder}
          data={detail.options}
          clearable
          searchable
          nothingFoundMessage={detail.nothingFound}
          value={detail.value}
          onChange={detail.onChange}
          error={detail.error}
        />
      )}
      {detail?.type === 'text' && (
        <Textarea
          label={detail.label}
          description={detail.description}
          placeholder={detail.placeholder}
          autosize
          minRows={2}
          maxLength={detail.maxLength}
          value={detail.value}
          onChange={(e) => detail.onChange(e.currentTarget.value)}
          error={detail.error}
        />
      )}
    </Stack>
  );
}

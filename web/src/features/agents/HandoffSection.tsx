import {
  Alert,
  Anchor,
  Badge,
  Button,
  Checkbox,
  Group,
  Select,
  Slider,
  Stack,
  Switch,
  Text,
  Textarea,
} from '@mantine/core';
import { Link } from 'react-router';
import type { FieldError } from '@/api/errors';
import { QueryState } from '@/components/QueryState';
import { type AreaRow, useAreas, useHoldMusic } from '@/features/team/api';
import { scheduleLabel } from '@/features/team/schedule';
import { type Draft, type HandoffDraft, MAX_HANDOFF_AREAS } from './draft';

const trackLabel = (t: string) => (t === 'default' ? 'Música de espera estándar' : t);

/** Mensaje del error de la ruta (del guardado), o undefined. */
const errorAt = (errors: FieldError[], path: string) => errors.find((e) => e.path === path)?.message;

function AreaItem({
  area,
  index,
  when,
  disabled,
  errors,
  onToggle,
  onWhen,
}: {
  area: AreaRow;
  /** Posicion en draft.handoff.areas (-1: no marcada). */
  index: number;
  when: string;
  disabled: boolean;
  errors: FieldError[];
  onToggle: (on: boolean) => void;
  onWhen: (when: string) => void;
}) {
  const on = index >= 0;
  return (
    <div className="def-item" style={{ padding: 'var(--mantine-spacing-sm)' }}>
      <Group gap="xs" wrap="wrap" mb={4}>
        <Text size="sm" fw={600}>
          {area.name}
        </Text>
        {!area.active && <Badge color="gray">Inactiva</Badge>}
      </Group>
      {area.schedule_text && (
        <Text size="xs" c="dimmed" mb="xs">
          {scheduleLabel(area.schedule_text)}
        </Text>
      )}
      <Checkbox
        label="Puede pasarle llamadas"
        description={!area.active && on ? 'Mientras esté inactiva, el agente no la ofrece.' : undefined}
        checked={on}
        disabled={disabled && !on}
        error={on ? errorAt(errors, `handoff.areas.${index}.area_id`) : undefined}
        onChange={(e) => onToggle(e.currentTarget.checked)}
      />
      {on && (
        <Textarea
          mt="sm"
          label="Cuándo pasarla"
          description="Para el agente: en qué casos le pasa la llamada a esta área. Vacío = la descripción del área."
          placeholder={area.description || 'Cuando pide hablar con una persona de ventas.'}
          autosize
          minRows={1}
          maxRows={4}
          maxLength={500}
          value={when}
          error={errorAt(errors, `handoff.areas.${index}.when`)}
          onChange={(e) => onWhen(e.currentTarget.value)}
        />
      )}
    </div>
  );
}

/** Derivacion a personas (docs/DERIVACIONES_PLAN.md): a que areas del equipo puede pasar la llamada el
 * agente y la musica mientras el cliente espera. */
export function HandoffEditor({
  draft,
  update,
  clientId,
  errors = [],
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  clientId: string;
  /** Errores del servidor (guardado), con su ruta: van en cada campo. */
  errors?: FieldError[];
}) {
  const areas = useAreas(clientId);
  const tracks = useHoldMusic();
  const h = draft.handoff;
  const set = (fn: (h: HandoffDraft) => HandoffDraft) => update((d) => ({ ...d, handoff: fn(d.handoff) }));
  const setMusic = (patch: Partial<HandoffDraft['holdMusic']>) =>
    set((x) => ({ ...x, holdMusic: { ...x.holdMusic, ...patch } }));

  const teamLink = '/team';
  return (
    <QueryState query={areas}>
      {(list) => {
        const known = new Set(list.map((a) => a.id));
        const missing = h.areas.map((a, i) => ({ ...a, i })).filter((a) => !known.has(a.areaId));
        const full = h.areas.length >= MAX_HANDOFF_AREAS;
        const trackOptions = [...(tracks.data ?? ['default'])];
        if (!trackOptions.includes(h.holdMusic.track)) trackOptions.push(h.holdMusic.track);
        return (
          <Stack gap="sm">
            {list.length === 0 ? (
              <Alert color="blue">
                <Text size="sm">
                  Este cliente todavía no tiene áreas.{' '}
                  <Anchor component={Link} to={teamLink} inherit>
                    Crealas en Equipo
                  </Anchor>{' '}
                  (por ejemplo Ventas o Administración, con las personas que atienden y su horario) y después
                  elegí acá a cuáles puede pasar la llamada.
                </Text>
              </Alert>
            ) : (
              <Stack gap="xs">
                {list.map((a) => {
                  const i = h.areas.findIndex((x) => x.areaId === a.id);
                  return (
                    <AreaItem
                      key={a.id}
                      area={a}
                      index={i}
                      when={i >= 0 ? h.areas[i]!.when : ''}
                      disabled={full}
                      errors={errors}
                      onToggle={(on) =>
                        set((x) => ({
                          ...x,
                          areas: on
                            ? [...x.areas, { areaId: a.id, when: '' }]
                            : x.areas.filter((y) => y.areaId !== a.id),
                        }))
                      }
                      onWhen={(when) =>
                        set((x) => ({
                          ...x,
                          areas: x.areas.map((y) => (y.areaId === a.id ? { ...y, when } : y)),
                        }))
                      }
                    />
                  );
                })}
                {full && (
                  <Text size="xs" c="dimmed">
                    Hasta {MAX_HANDOFF_AREAS} áreas por agente.
                  </Text>
                )}
              </Stack>
            )}
            {missing.map((a) => (
              <Alert key={a.areaId} color="yellow" title="Un área ya no existe">
                <Group justify="space-between" gap="xs">
                  <Text size="sm">
                    {errorAt(errors, `handoff.areas.${a.i}.area_id`) ?? 'Se borró en Equipo.'} Sacala para
                    poder guardar.
                  </Text>
                  <Button
                    size="compact-sm"
                    variant="subtle"
                    color="red"
                    onClick={() =>
                      set((x) => ({ ...x, areas: x.areas.filter((y) => y.areaId !== a.areaId) }))
                    }
                  >
                    Sacar
                  </Button>
                </Group>
              </Alert>
            ))}

            {h.areas.length > 0 && (
              <Stack gap="sm" pt="xs">
                <Switch
                  label="Música de espera"
                  description="Suena mientras el cliente espera que atienda la persona del equipo."
                  checked={h.holdMusic.enabled}
                  onChange={(e) => setMusic({ enabled: e.currentTarget.checked })}
                />
                {h.holdMusic.enabled && (
                  <>
                    <Select
                      label="Tema"
                      data={trackOptions.map((t) => ({ value: t, label: trackLabel(t) }))}
                      value={h.holdMusic.track}
                      onChange={(v) => v && setMusic({ track: v })}
                      allowDeselect={false}
                      error={errorAt(errors, 'handoff.hold_music.track')}
                      maw={360}
                    />
                    <Stack gap={4} maw={360}>
                      <Text size="sm" fw={600} id="hold-volume">
                        Volumen{' '}
                        <Text span size="sm" c="dimmed" className="mono">
                          {Math.round(h.holdMusic.volume * 100)} %
                        </Text>
                      </Text>
                      <Slider
                        aria-labelledby="hold-volume"
                        min={5}
                        max={100}
                        step={5}
                        value={Math.round(h.holdMusic.volume * 100)}
                        onChange={(v) => setMusic({ volume: v / 100 })}
                        label={(v) => `${v} %`}
                        marks={[
                          { value: 5, label: '5 %' },
                          { value: 100, label: '100 %' },
                        ]}
                        mb="md"
                      />
                      {errorAt(errors, 'handoff.hold_music.volume') && (
                        <Text size="xs" c="red">
                          {errorAt(errors, 'handoff.hold_music.volume')}
                        </Text>
                      )}
                    </Stack>
                  </>
                )}
              </Stack>
            )}
          </Stack>
        );
      }}
    </QueryState>
  );
}

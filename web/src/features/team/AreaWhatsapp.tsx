import { Alert, Anchor, Autocomplete, NumberInput, Select, Stack, Text } from '@mantine/core';
import { Link } from 'react-router';
import type { WaTemplate } from '@/api/types';
import { QueryState } from '@/components/QueryState';
import { useFeatureLock } from '@/features/billing/features';
import { useWaAccounts, useWaTemplates } from '@/features/whatsapp/api';
import { placeholderNumbers, templateBody } from '@/features/whatsapp/templates';
import { BASE_VARIABLES, type TemplateDraft, WAIT_SECONDS, type WhatsappDraft } from './whatsappDraft';

const key = (name: string, language: string) => `${name}::${language}`;

/** Botones de respuesta rapida del cuerpo de una plantilla de Meta. */
function hasQuickReply(t: WaTemplate): boolean {
  const buttons = (t.components ?? []).find((c) => String(c.type).toUpperCase() === 'BUTTONS');
  const list = Array.isArray(buttons?.buttons) ? (buttons.buttons as { type?: unknown }[]) : [];
  return list.some((b) => String(b.type).toUpperCase() === 'QUICK_REPLY');
}

function hasButtons(t: WaTemplate): boolean {
  return (t.components ?? []).some((c) => String(c.type).toUpperCase() === 'BUTTONS');
}

/** Una plantilla del area: cual es y el valor de cada {{n}} de su cuerpo. */
function TemplateField({
  label,
  description,
  templates,
  value,
  onChange,
  variables,
  expect,
}: {
  label: string;
  description: string;
  /** Las aprobadas de la cuenta. */
  templates: WaTemplate[];
  value: TemplateDraft | null;
  onChange: (next: TemplateDraft | null) => void;
  variables: string[];
  /** Si la plantilla tiene que llevar boton de respuesta rapida (rotacion), no llevarlo, o da igual. */
  expect: 'button' | 'no_button';
}) {
  const options = templates.map((t) => ({
    value: key(t.name, t.language),
    label: `${t.name} · ${t.language}`,
  }));
  const current = value ? key(value.name, value.language) : null;
  if (value && current && !options.some((o) => o.value === current))
    options.push({ value: current, label: `${value.name} · ${value.language} (no aprobada)` });
  const picked = templates.find((t) => value && t.name === value.name && t.language === value.language);
  const count = picked
    ? placeholderNumbers(templateBody(picked.components ?? [])).length
    : (value?.params.length ?? 0);

  const pick = (k: string | null) => {
    const t = templates.find((x) => key(x.name, x.language) === k);
    if (!t) return onChange(null);
    const n = placeholderNumbers(templateBody(t.components ?? [])).length;
    onChange({
      name: t.name,
      language: t.language,
      params: Array.from({ length: n }, (_, i) => value?.params[i] ?? ''),
    });
  };
  const setParam = (i: number, text: string) =>
    value && onChange({ ...value, params: value.params.map((p, j) => (j === i ? text : p)) });

  return (
    <Stack gap="xs">
      <Select
        label={label}
        description={description}
        placeholder="Ninguna"
        data={options}
        value={current}
        onChange={pick}
        searchable
        clearable
        nothingFoundMessage="No hay plantillas aprobadas"
      />
      {picked && (
        <Text size="xs" c="dimmed" style={{ whiteSpace: 'pre-line' }} lineClamp={4}>
          {templateBody(picked.components ?? [])}
        </Text>
      )}
      {picked && expect === 'button' && !hasQuickReply(picked) && (
        <Text size="xs" c="yellow.8">
          Esta plantilla no tiene un botón de respuesta rápida: nadie podría aceptar tocándolo. Creá una con
          el botón en Plantillas.
        </Text>
      )}
      {picked && expect === 'no_button' && hasButtons(picked) && (
        <Text size="xs" c="yellow.8">
          Esta plantilla tiene botones y acá tiene que ir sin ellos.
        </Text>
      )}
      {value &&
        Array.from({ length: count }, (_, i) => (
          <Autocomplete
            key={i}
            label={`Valor de {{${i + 1}}}`}
            description={
              i === 0
                ? 'Elegí uno o escribí un dato que traiga la herramienta de «Antes de la conversación» del agente. Si ese dato no llega, va «-».'
                : undefined
            }
            data={variables}
            value={value.params[i] ?? ''}
            onChange={(text) => setParam(i, text)}
            classNames={{ input: 'mono' }}
            maxLength={40}
            maw={320}
          />
        ))}
    </Stack>
  );
}

/**
 * WhatsApp de un area (docs/features/EQUIPO_TELEFONIA.md): el numero, las plantillas aprobadas y la espera.
 * En un area de llamada, la plantilla rota entre las personas y la de la llamada acompana al timbre; en un area
 * de aviso, la plantilla es el aviso.
 */
export function AreaWhatsapp({
  value,
  onChange,
  delivery,
}: {
  value: WhatsappDraft;
  onChange: (next: WhatsappDraft) => void;
  delivery: 'call' | 'whatsapp';
}) {
  const lock = useFeatureLock('whatsapp');
  if (lock.locked)
    return (
      <Alert color="yellow">
        <Text size="sm">
          Tu plan {lock.tierName} no incluye WhatsApp:{' '}
          {delivery === 'whatsapp' ? 'esta área no podrá avisar' : 'el área no podrá avisar por ahí'}.{' '}
          <Anchor component={Link} to="/plan" inherit>
            Ver el plan
          </Anchor>
        </Text>
      </Alert>
    );
  return <WhatsappConnected value={value} onChange={onChange} delivery={delivery} />;
}

function WhatsappConnected({
  value,
  onChange,
  delivery,
}: {
  value: WhatsappDraft;
  onChange: (next: WhatsappDraft) => void;
  delivery: 'call' | 'whatsapp';
}) {
  const accounts = useWaAccounts();
  const notice = delivery === 'whatsapp';
  const templates = useWaTemplates(value.accountId || undefined);
  const approved = (templates.data ?? []).filter((t) => t.status === 'APPROVED');
  // `cliente` (el telefono de la persona) solo en el aviso: antes de aceptar no se entrega.
  const noticeVars = BASE_VARIABLES;
  const rotationVars = BASE_VARIABLES.filter((v) => v !== 'cliente');

  return (
    <QueryState query={accounts}>
      {(list) => {
        const usable = list.filter((a) => a.active && a.status === 'connected');
        const options = usable.map((a) => ({
          value: a.id,
          label: a.name ? `${a.display_phone_number} · ${a.name}` : a.display_phone_number,
        }));
        const saved = list.find((a) => a.id === value.accountId);
        if (saved && !usable.includes(saved))
          options.push({ value: saved.id, label: `${saved.display_phone_number} (no conectado)` });
        if (!options.length)
          return (
            <Text size="sm" c="dimmed">
              No hay un número de WhatsApp conectado.{' '}
              <Anchor component={Link} to="/whatsapp" inherit>
                Conectá uno en WhatsApp
              </Anchor>{' '}
              para avisar a las personas del equipo.
            </Text>
          );
        return (
          <Stack gap="sm">
            <Select
              label="Número que envía"
              description={
                notice
                  ? 'Desde acá sale el aviso. Lo recibe una sola persona: la primera del área con «Recibe WhatsApp».'
                  : 'Desde acá salen los avisos a las personas del equipo con «Recibe WhatsApp».'
              }
              placeholder="Sin WhatsApp"
              data={options}
              value={value.accountId || null}
              onChange={(id) =>
                onChange(
                  id === value.accountId
                    ? value
                    : // Las plantillas son de la cuenta: al cambiarla se eligen de nuevo.
                      { ...value, accountId: id ?? '', template: null, callTemplate: null },
                )
              }
              clearable
              maw={420}
            />
            {value.accountId && (
              <QueryState query={templates}>
                {() => (
                  <Stack gap="md">
                    <TemplateField
                      label={notice ? 'Plantilla del aviso' : 'Plantilla de rotación'}
                      description={
                        notice
                          ? 'Es lo que recibe la persona. Sin botón.'
                          : 'Se la manda a una persona por vez; acepta tocando el botón de respuesta rápida. Si hay llamada, se usa antes de ella.'
                      }
                      templates={approved}
                      value={value.template}
                      onChange={(template) => onChange({ ...value, template })}
                      variables={notice ? noticeVars : rotationVars}
                      expect={notice ? 'no_button' : 'button'}
                    />
                    {!notice && (
                      <TemplateField
                        label="Plantilla de la llamada"
                        description="Acompaña al timbre: avisa que están llamando. Sin botón, para que no toquen Aceptar en vez de atender."
                        templates={approved}
                        value={value.callTemplate}
                        onChange={(callTemplate) => onChange({ ...value, callTemplate })}
                        variables={rotationVars}
                        expect="no_button"
                      />
                    )}
                    {!notice && value.template && (
                      <NumberInput
                        label="Espera por persona"
                        description="Segundos que espera a que acepte antes de pasar a la siguiente."
                        min={WAIT_SECONDS.min}
                        max={WAIT_SECONDS.max}
                        suffix=" s"
                        allowDecimal={false}
                        allowNegative={false}
                        value={value.waitSeconds}
                        onChange={(waitSeconds) => onChange({ ...value, waitSeconds })}
                        w={{ base: '100%', xs: 260 }}
                      />
                    )}
                  </Stack>
                )}
              </QueryState>
            )}
          </Stack>
        );
      }}
    </QueryState>
  );
}

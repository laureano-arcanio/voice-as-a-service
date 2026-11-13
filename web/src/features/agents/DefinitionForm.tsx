import {
  ActionIcon,
  Autocomplete,
  Badge,
  Button,
  Card,
  Collapse,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  TagsInput,
  Text,
  TextInput,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { IconArrowDown, IconArrowUp, IconChevronDown, IconPlus, IconTrash } from '@tabler/icons-react';
import { createContext, type ReactNode, useContext } from 'react';
import type { FieldError } from '@/api/errors';
import { PlanGate } from '@/components/PlanGate';
import { PromptEditor, VariableField, type ExtraVariable } from '@/components/variables';
import { useTools } from '@/features/tools/api';
import { VoiceSelect } from '@/features/voices/VoiceSelect';
import {
  type ConditionDraft,
  type ConditionValue,
  type Draft,
  FIELD_TYPES,
  type FieldDraft,
  FIRST_MESSAGE_DELAY_MS,
  hasPhoneField,
  type FieldType,
  MAX_FIRST_MESSAGE,
  MAX_PROMPT,
  move,
  newField,
  newKey,
  newOutcome,
  type OutcomeDraft,
  type Part,
  renameField,
  SECTION_PART,
  sectionId,
  withPhoneField,
} from './draft';
import { ExternalSection } from './ExternalSection';
import { HandoffEditor } from './HandoffSection';
import { LlmSection } from './LlmSection';
import { WorkflowsEditor } from './WorkflowsSection';
import { SecretsSection } from './SecretsSection';
import { neededSecrets } from './grants';
import { ClientToolsEditor } from './ToolsSection';
import { VariablesSection } from './VariablesSection';

const LANGUAGES = ['es-AR', 'es-UY', 'es-CL', 'es-MX', 'es-ES', 'en-US', 'pt-BR'];
const TYPE_LABEL: Record<string, string> = Object.fromEntries(FIELD_TYPES.map((t) => [t.value, t.label]));

/** La pestaña que se esta editando: cada seccion se muestra solo en la suya (SECTION_PART). */
const PartContext = createContext<Part>('conversacion');

/** Mensaje del error del servidor para esa ruta, o undefined. */
const errorAt = (errors: FieldError[], path: string) => errors.find((e) => e.path === path)?.message;

/** Los errores de una ruta con sus hijos (`analysis.outcomes.ok.`). */
const errorsUnder = (errors: FieldError[], prefix: string) =>
  errors.filter((e) => e.path === prefix || e.path.startsWith(`${prefix}.`));

function Section({
  name,
  title,
  description,
  actions,
  children,
}: {
  name: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const part = useContext(PartContext);
  if (SECTION_PART[name] !== part) return null;
  return (
    <Card id={sectionId(name)} style={{ scrollMarginTop: 140 }}>
      <Group justify="space-between" align="flex-start" mb={description ? 4 : 'sm'} wrap="nowrap">
        <Title order={4}>{title}</Title>
        {actions}
      </Group>
      {description && (
        <Text size="xs" c="dimmed" mb="sm">
          {description}
        </Text>
      )}
      {children}
    </Card>
  );
}

function IconAction({
  label,
  onClick,
  disabled,
  color,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  color?: string;
  children: ReactNode;
}) {
  return (
    <Tooltip label={label} withArrow>
      <ActionIcon
        variant={color ? 'subtle' : 'default'}
        color={color}
        aria-label={label}
        onClick={onClick}
        disabled={disabled}
      >
        {children}
      </ActionIcon>
    </Tooltip>
  );
}

/** Bloque plegable de un dato o un resultado: un bloque de 12 px de radio dentro de la tarjeta. */
function ItemBlock({
  id,
  opened,
  onToggle,
  summary,
  actions,
  children,
}: {
  id: string;
  opened: boolean;
  onToggle: () => void;
  summary: ReactNode;
  actions: ReactNode;
  children: ReactNode;
}) {
  return (
    <div id={id} className="def-item" style={{ scrollMarginTop: 140 }}>
      <Group justify="space-between" wrap="nowrap" gap="xs">
        <UnstyledButton
          className="card-toggle"
          onClick={onToggle}
          aria-expanded={opened}
          style={{ flex: 1, minWidth: 0 }}
        >
          <div style={{ minWidth: 0 }}>{summary}</div>
          <IconChevronDown size={18} className="chevron" aria-hidden />
        </UnstyledButton>
        <Group gap={4} wrap="nowrap">
          {actions}
        </Group>
      </Group>
      <Collapse in={opened}>
        <Stack gap="sm" pt="md">
          {children}
        </Stack>
      </Collapse>
    </div>
  );
}

// ---------- condiciones ----------

function ValueInput({
  field,
  value,
  onChange,
}: {
  field: FieldDraft | undefined;
  value: ConditionValue | null;
  onChange: (v: ConditionValue | null) => void;
}) {
  const common = { label: 'Valor', style: { flex: 1, minWidth: 140 } } as const;
  if (field?.type === 'boolean')
    return (
      <Select
        {...common}
        data={[
          { value: 'true', label: 'Sí' },
          { value: 'false', label: 'No' },
        ]}
        value={value === null ? null : String(value)}
        onChange={(v) => onChange(v === null ? null : v === 'true')}
        allowDeselect={false}
      />
    );
  if (field?.type === 'choice')
    return (
      <Select
        {...common}
        data={field.options}
        value={value === null ? null : String(value)}
        onChange={(v) => onChange(v)}
        allowDeselect={false}
      />
    );
  if (field?.type === 'integer')
    return (
      <NumberInput
        {...common}
        value={typeof value === 'number' ? value : ''}
        onChange={(v) => onChange(typeof v === 'number' ? v : null)}
        allowDecimal={false}
        min={0}
      />
    );
  return (
    <TextInput
      {...common}
      value={value === null ? '' : String(value)}
      onChange={(e) => onChange(e.currentTarget.value)}
    />
  );
}

/** Condiciones "dato = valor" (todas se tienen que cumplir). */
function ConditionsEditor({
  conditions,
  fields,
  onChange,
  intro,
}: {
  conditions: ConditionDraft[];
  fields: FieldDraft[];
  onChange: (c: ConditionDraft[]) => void;
  intro: string;
}) {
  const byName = new Map(fields.map((f) => [f.name, f]));
  const set = (i: number, c: Partial<ConditionDraft>) =>
    onChange(conditions.map((x, j) => (j === i ? { ...x, ...c } : x)));
  return (
    <Stack gap="xs">
      <Text size="sm" fw={600}>
        {intro}
      </Text>
      {conditions.map((c, i) => (
        <Group key={c.key} gap="xs" align="flex-end" wrap="wrap">
          <Select
            label="Dato"
            data={fields.map((f) => ({ value: f.name, label: f.label ? `${f.label} (${f.name})` : f.name }))}
            value={c.field || null}
            onChange={(v) =>
              set(i, { field: v ?? '', value: byName.get(v ?? '')?.type === 'boolean' ? true : null })
            }
            allowDeselect={false}
            searchable
            style={{ flex: 1, minWidth: 160 }}
          />
          <ValueInput field={byName.get(c.field)} value={c.value} onChange={(value) => set(i, { value })} />
          <IconAction
            label="Quitar condición"
            color="red"
            onClick={() => onChange(conditions.filter((_, j) => j !== i))}
          >
            <IconTrash size={18} />
          </IconAction>
        </Group>
      ))}
      <Button
        variant="subtle"
        size="compact-sm"
        leftSection={<IconPlus size={16} />}
        w="fit-content"
        disabled={!fields.length}
        onClick={() => onChange([...conditions, { key: newKey(), field: '', value: null }])}
      >
        Agregar condición
      </Button>
    </Stack>
  );
}

function conditionsText(conditions: ConditionDraft[], fields: FieldDraft[]): string {
  const names = new Map(fields.map((f) => [f.name, f.label || f.name]));
  const show = (v: ConditionValue | null) => (v === true ? 'sí' : v === false ? 'no' : String(v ?? '…'));
  return conditions.map((c) => `${names.get(c.field) ?? (c.field || '…')} = ${show(c.value)}`).join(' y ');
}

// ---------- datos del análisis ----------

function FieldEditor({
  field,
  index,
  draft,
  opened,
  onToggle,
  update,
  errors = [],
}: {
  field: FieldDraft;
  index: number;
  draft: Draft;
  opened: boolean;
  onToggle: () => void;
  update: (fn: (d: Draft) => Draft) => void;
  errors?: FieldError[];
}) {
  const path = `analysis.fields.${index}`;
  const set = (patch: Partial<FieldDraft>) =>
    update((d) => ({
      ...d,
      analysis: {
        ...d.analysis,
        fields: d.analysis.fields.map((f, i) => (i === index ? { ...f, ...patch } : f)),
      },
    }));
  const usedBy = draft.analysis.outcomes.some((o) => o.conditions.some((c) => c.field === field.name));

  return (
    <ItemBlock
      id={sectionId(`dato-${field.key}`)}
      opened={opened}
      onToggle={onToggle}
      summary={
        <Group gap="xs" wrap="wrap">
          <Text span fw={600}>
            {field.label || field.name || 'Sin nombre'}
          </Text>
          {field.label && (
            <Text span className="mono" c="dimmed">
              {field.name}
            </Text>
          )}
          <Badge color="gray">{TYPE_LABEL[field.type] ?? field.type}</Badge>
        </Group>
      }
      actions={
        <IconAction
          label="Quitar dato"
          color="red"
          onClick={() =>
            update((d) => ({
              ...d,
              analysis: { ...d.analysis, fields: d.analysis.fields.filter((_, i) => i !== index) },
            }))
          }
        >
          <IconTrash size={18} />
        </IconAction>
      }
    >
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          label="Etiqueta"
          description="Cómo se muestra en el dashboard."
          placeholder="Teléfono de contacto"
          value={field.label}
          onChange={(e) => set({ label: e.currentTarget.value })}
        />
        <TextInput
          label="Nombre interno"
          description={
            usedBy
              ? 'Clave del dato. Al cambiarla se actualizan las condiciones que lo usan.'
              : 'Clave del dato: minúsculas, números y _.'
          }
          placeholder="telefono"
          classNames={{ input: 'mono' }}
          value={field.name}
          error={errorAt(errors, `${path}.name`)}
          onChange={(e) => {
            const name = e.currentTarget.value.toLowerCase().replace(/[^a-z0-9_]/g, '_');
            update((d) => renameField(d, index, name));
          }}
        />
        <Select
          label="Tipo"
          data={[
            ...FIELD_TYPES.map((t) => ({ value: t.value, label: t.label })),
            ...(FIELD_TYPES.some((t) => t.value === field.type)
              ? []
              : [{ value: field.type, label: field.type }]),
          ]}
          value={field.type}
          onChange={(v) => v && set({ type: v as FieldType })}
          allowDeselect={false}
          error={errorAt(errors, `${path}.type`)}
        />
      </SimpleGrid>
      {field.type === 'choice' && (
        <TagsInput
          label="Opciones"
          description="Los valores posibles. Enter o coma para agregar cada una."
          placeholder="si, no, dudas"
          value={field.options}
          onChange={(options) => set({ options })}
          error={errorAt(errors, `${path}.options`)}
          clearable
        />
      )}
      <VariableField
        label="Descripción"
        description="Qué es el dato y cómo se interpreta: la extracción la usa para sacar el valor. Puede nombrar variables."
        field="analysis"
        declared={declaredOf(draft)}
        multiline
        minRows={2}
        maxRows={8}
        value={field.description}
        onChange={(description) => set({ description })}
        error={errorAt(errors, `${path}.description`)}
      />
    </ItemBlock>
  );
}

// ---------- resultados ----------

function OutcomeEditor({
  outcome,
  index,
  draft,
  opened,
  onToggle,
  update,
  errors = [],
}: {
  outcome: OutcomeDraft;
  index: number;
  draft: Draft;
  opened: boolean;
  onToggle: () => void;
  update: (fn: (d: Draft) => Draft) => void;
  errors?: FieldError[];
}) {
  const last = draft.analysis.outcomes.length - 1;
  const isDefault = index === last;
  // Con el agente del cliente no hay datos: el resultado lo elige su agente (end_call), no las condiciones.
  const external = draft.external !== null;
  const set = (patch: Partial<OutcomeDraft>) =>
    update((d) => ({
      ...d,
      analysis: {
        ...d.analysis,
        outcomes: d.analysis.outcomes.map((o, i) => (i === index ? { ...o, ...patch } : o)),
      },
    }));
  // El ultimo (por defecto) queda fijo al final.
  const shift = (to: number) =>
    update((d) => ({ ...d, analysis: { ...d.analysis, outcomes: move(d.analysis.outcomes, index, to) } }));
  const path = `analysis.outcomes.${index}`;
  const own = errorsUnder(errors, path);

  return (
    <ItemBlock
      id={sectionId(`resultado-${outcome.key}`)}
      opened={opened}
      onToggle={onToggle}
      summary={
        <Group gap="xs" wrap="wrap">
          <Text span fw={600}>
            {outcome.label || outcome.id || 'Sin nombre'}
          </Text>
          <Text span className="mono" c="dimmed">
            {outcome.id}
          </Text>
          {outcome.goal && <Badge color="green">Cumple el objetivo</Badge>}
          <Badge color="gray">
            {isDefault
              ? external
                ? 'Si tu agente no elige otro'
                : 'En cualquier otro caso'
              : external
                ? 'Lo elige tu agente'
                : outcome.conditions.length
                  ? `Si ${conditionsText(outcome.conditions, draft.analysis.fields)}`
                  : 'Sin condiciones'}
          </Badge>
        </Group>
      }
      actions={
        isDefault ? null : (
          <>
            <IconAction label="Subir" onClick={() => shift(index - 1)} disabled={index === 0}>
              <IconArrowUp size={18} />
            </IconAction>
            <IconAction label="Bajar" onClick={() => shift(index + 1)} disabled={index >= last - 1}>
              <IconArrowDown size={18} />
            </IconAction>
            <IconAction
              label="Quitar resultado"
              color="red"
              onClick={() =>
                update((d) => ({
                  ...d,
                  analysis: {
                    ...d.analysis,
                    outcomes: d.analysis.outcomes.filter((_, i) => i !== index),
                  },
                }))
              }
            >
              <IconTrash size={18} />
            </IconAction>
          </>
        )
      }
    >
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          label="Etiqueta"
          description="Cómo se muestra en el dashboard."
          placeholder="Demo agendada"
          value={outcome.label}
          onChange={(e) => set({ label: e.currentTarget.value })}
        />
        <TextInput
          label="ID"
          description="Minúsculas, números y _. Queda en cada conversación."
          placeholder="demo"
          classNames={{ input: 'mono' }}
          value={outcome.id}
          error={errorAt(errors, `${path}.id`)}
          onChange={(e) => set({ id: e.currentTarget.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
        />
      </SimpleGrid>
      <Switch
        label="Cumple el objetivo"
        description="Cuenta como éxito en las métricas."
        checked={outcome.goal}
        onChange={(e) => set({ goal: e.currentTarget.checked })}
      />
      <Switch
        label="No volver a llamar"
        description="En una campaña de llamadas, el teléfono pasa a la lista de bajas de voz del cliente y ninguna campaña lo vuelve a llamar."
        checked={outcome.noContact}
        onChange={(e) => set({ noContact: e.currentTarget.checked })}
      />
      {external ? null : isDefault ? (
        <Text size="xs" c="dimmed">
          Es el resultado por defecto: aplica cuando no se cumple ningún otro. Va siempre último y sin
          condiciones.
        </Text>
      ) : (
        <ConditionsEditor
          intro="Aplica si se cumplen todas estas condiciones:"
          conditions={outcome.conditions}
          fields={draft.analysis.fields}
          onChange={(conditions) => set({ conditions })}
        />
      )}
      {own.length > 0 && (
        <Stack gap={2}>
          {own.map((e, i) => (
            <Text key={i} size="xs" c="red">
              {e.message}
            </Text>
          ))}
        </Stack>
      )}
    </ItemBlock>
  );
}

/** Las variables declaradas, como las reciben los editores de texto. */
function declaredOf(draft: Draft) {
  return draft.variables
    .filter((v) => v.name.trim())
    .map((v) => ({ name: v.name.trim(), description: v.description }));
}

// ---------- formulario ----------

export function DefinitionForm({
  part,
  draft,
  update,
  opened,
  toggle,
  voiceSeed,
  clientId,
  errors = [],
  agentId,
}: {
  /** La pestaña de edicion: solo se muestran sus secciones. */
  part: Part;
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  /** Claves de los datos y resultados desplegados. */
  opened: Set<string>;
  toggle: (key: string, open?: boolean) => void;
  /** Para reiniciar el texto de la prueba de voz al cambiar de agente. */
  voiceSeed: string;
  /** Cliente del agente: sus herramientas, conexiones y áreas. */
  clientId: string;
  /** Errores del servidor con su ruta, para mostrarlos en el campo. */
  errors?: FieldError[];
  /** El agente ya guardado: sus secretos se cargan aparte de la definición. */
  agentId?: string;
}) {
  const set = (patch: Partial<Draft>) => update((d) => ({ ...d, ...patch }));
  // Con el agente del cliente, el prompt, el modelo y los datos son suyos: esas secciones no aplican.
  const external = draft.external !== null;
  const clientTools = useTools(external ? undefined : clientId);
  const declared = declaredOf(draft);
  // Lo que asigna el pre-call: los textos lo pueden nombrar. Las ocultas no se ofrecen (no llegan al LLM).
  const preCall = draft.workflows.preCall?.tool;
  const preTool = (clientTools.data ?? []).find((t) => t.slug === preCall);
  const assigns = (preTool?.definition as { assign?: { var?: unknown; hide?: unknown }[] } | undefined)
    ?.assign;
  const extra: ExtraVariable[] = (Array.isArray(assigns) ? assigns : [])
    .filter((a) => typeof a.var === 'string' && a.var && !a.hide)
    .map((a) => ({ name: a.var as string, description: `Lo asigna el pre-call (${preCall})` }));
  const summaryError = errorsUnder(errors, 'analysis.summary').length
    ? errorsUnder(errors, 'analysis.summary')[0]!.message
    : undefined;

  return (
    <PartContext.Provider value={part}>
      <Stack gap="md">
        <Section
          name="agente"
          title="Agente"
          description={
            external
              ? 'Quién es. Con tu propio agente, cómo responde lo decide tu agente.'
              : 'Quién es. Cómo habla está en el prompt.'
          }
        >
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label="Nombre"
              description="Cómo se presenta."
              placeholder="Sofía"
              value={draft.name}
              onChange={(e) => set({ name: e.currentTarget.value })}
              error={errorAt(errors, 'agent.name')}
            />
            <Autocomplete
              label="Idioma"
              description="Código, como es-AR."
              data={LANGUAGES}
              value={draft.language}
              onChange={(language) => set({ language })}
              error={errorAt(errors, 'agent.language')}
            />
          </SimpleGrid>
        </Section>

        <Section
          name="externo"
          title="Tu propio agente"
          description="Si ya tenés tu agente armado, Atentina le pone la voz y el teléfono."
        >
          <ExternalSection draft={draft} update={update} clientId={clientId} errors={errors} />
        </Section>

        {!external && (
          <Section
            name="herramientas"
            title="Herramientas"
            description="Lo que el agente puede hacer durante la conversación: consultar o registrar datos en tu sistema."
          >
            <Stack gap="md">
              <PlanGate feature="custom_tools" what="herramientas para tus agentes">
                <Stack gap="md">
                  <ClientToolsEditor draft={draft} update={update} clientId={clientId} agentId={agentId} />
                  <SecretsSection
                    clientId={clientId}
                    agentId={agentId}
                    needed={neededSecrets(draft, clientTools.data)}
                  />
                </Stack>
              </PlanGate>
            </Stack>
          </Section>
        )}

        <Section
          name="voz"
          title="Voz"
          description="Con la que habla en las llamadas y las notas de voz. Elegila y escuchala acá mismo. Abajo, qué guarda de cada conversación."
        >
          <Stack gap="sm">
            <VoiceSelect
              key={voiceSeed}
              value={draft.voice}
              onChange={(voice) => set({ voice })}
              previewText={draft.firstMessage}
            />
            <Switch
              label="Grabar audio"
              description="Un archivo por turno (la llamada completa, telefónica o de WhatsApp), localmente en el servidor."
              checked={draft.recordAudio}
              onChange={(e) => set({ recordAudio: e.currentTarget.checked })}
            />
            {draft.recordAudio && (
              <Switch
                ml="xl"
                label="Avisar que la llamada se graba"
                description="Antes del saludo, el agente dice: “Esta llamada está siendo grabada.”"
                checked={draft.recordingNotice}
                onChange={(e) => set({ recordingNotice: e.currentTarget.checked })}
              />
            )}
            <Switch
              label="Resumen por email después de cada llamada"
              description={
                <>
                  Al cortar, Atentina le manda al cliente el resumen, los datos, el resultado y la
                  conversación. El cliente lo apaga o elige a quién le llega en Mi cuenta.
                  {draft.callSummaryEmail && (
                    <Text
                      component="span"
                      display="block"
                      size="xs"
                      mt={4}
                      c={external || hasPhoneField(draft) ? 'dimmed' : 'orange.8'}
                    >
                      {external
                        ? 'Con tu propio agente no se piden datos: en las llamadas por el link el email va sin teléfono.'
                        : hasPhoneField(draft)
                          ? 'El email lleva el teléfono: en las llamadas por teléfono es el número de quien llama (el agente no lo pregunta); por el link para llamar, lo pide (dato de tipo Teléfono).'
                          : 'Falta un dato de tipo Teléfono en el análisis: en las llamadas por el link el email va a ir sin teléfono.'}
                    </Text>
                  )}
                </>
              }
              checked={draft.callSummaryEmail}
              onChange={(e) => {
                const on = e.currentTarget.checked;
                update((d) =>
                  on ? withPhoneField({ ...d, callSummaryEmail: true }) : { ...d, callSummaryEmail: false },
                );
              }}
            />
            <NumberInput
              label="Ventana de contexto en WhatsApp (minutos)"
              description="Minutos sin mensaje del contacto para dar la conversación por terminada: la siguiente arranca de cero, sin el historial anterior. Vacío = el default del servidor (1440 min = 24 hs)."
              placeholder="1440"
              value={draft.waSessionMinutes ?? ''}
              onChange={(v) => set({ waSessionMinutes: typeof v === 'number' ? v : null })}
              min={1}
              max={60 * 24 * 90}
              allowDecimal={false}
              maw={260}
            />
          </Stack>
        </Section>

        <Section
          name="derivacion"
          title="Derivación a personas"
          description="A qué áreas del equipo puede pasar la llamada el agente, cuándo, y qué escucha el cliente mientras espera."
        >
          <HandoffEditor draft={draft} update={update} clientId={clientId} errors={errors} />
        </Section>

        <Section
          name="automaticas"
          title="Antes y después de la conversación"
          description="Herramientas que corre la plataforma sola, sin que el modelo las vea: una al empezar, para traer datos de la persona, y otra al terminar, para registrar lo que pasó."
        >
          <PlanGate feature="custom_tools" what="herramientas para tus agentes">
            <WorkflowsEditor draft={draft} update={update} clientId={clientId} errors={errors} />
          </PlanGate>
        </Section>

        {!external && (
          <Section
            name="modelo"
            title="Modelo de lenguaje"
            description="Qué modelo contesta y con qué parámetros."
          >
            <LlmSection draft={draft} update={update} clientId={clientId} />
          </Section>
        )}

        {!external && (
          <Section
            name="prompt"
            title="Prompt"
            description="Lo que el agente es y cómo conversa: va tal cual al modelo. Tipeá {{ para insertar una variable."
          >
            <PromptEditor
              field="prompt"
              label="Prompt"
              maxLength={MAX_PROMPT}
              minRows={16}
              declared={declared}
              extra={extra}
              value={draft.prompt}
              onChange={(prompt) => set({ prompt })}
              error={errorAt(errors, 'prompt')}
            />
          </Section>
        )}

        <Section
          name="primer_mensaje"
          title="Primer mensaje"
          description="Lo primero que dice en una llamada. Por WhatsApp entrante escribe primero la persona."
        >
          <Stack gap="sm">
            <PromptEditor
              field="first_message"
              label="Primer mensaje"
              maxLength={MAX_FIRST_MESSAGE}
              minRows={3}
              declared={declared}
              extra={extra}
              value={draft.firstMessage}
              onChange={(firstMessage) => set({ firstMessage })}
              error={errorAt(errors, 'first_message')}
            />
            <Switch
              label="Pregenerar el audio del primer mensaje"
              description="En las llamadas, el primer mensaje se sintetiza entero al guardar (suena más natural que frase por frase) y se reproduce ese audio. Se regenera en cada guardado. No aplica si el texto tiene {{variables}} (cambia en cada conversación) o la llamada usa otra voz."
              checked={draft.firstMessageAudio}
              onChange={(e) => set({ firstMessageAudio: e.currentTarget.checked })}
            />
            {draft.firstMessageAudio && draft.firstMessage.includes('{{') && (
              <Text size="xs" c="yellow.8">
                El primer mensaje tiene variables: no se pregenera el audio y se sintetiza en cada llamada.
              </Text>
            )}
            <NumberInput
              label="Espera antes del primer mensaje (ms)"
              description="En las llamadas, cuánto espera desde que se conecta hasta que empieza a hablar."
              value={draft.firstMessageDelayMs}
              onChange={(v) =>
                set({ firstMessageDelayMs: typeof v === 'number' ? v : FIRST_MESSAGE_DELAY_MS })
              }
              min={0}
              max={10_000}
              step={100}
              allowDecimal={false}
              maw={260}
              error={errorAt(errors, 'first_message_delay_ms')}
            />
          </Stack>
        </Section>

        {!external && (
          <Section
            name="variables"
            title="Variables"
            description="Valores que el agente nombra con {{nombre}}: su descripción y el valor por defecto. Los demás pueden venir del pedido de la llamada, del contacto o del pre-call."
          >
            <VariablesSection draft={draft} update={update} />
          </Section>
        )}

        <Section
          name="analisis"
          title="Análisis al terminar"
          description={
            external
              ? 'Con tu propio agente el análisis lo hace él: acá solo se eligen los resultados que puede devolver al llamar a end_call.'
              : 'Una llamada guiada al terminar saca los datos, el resumen y clasifica la conversación. Sin esto, el agente no extrae nada.'
          }
          actions={
            <Group gap="xs">
              {!external && (
                <Button
                  variant="default"
                  size="xs"
                  leftSection={<IconPlus size={16} />}
                  onClick={() => {
                    const f = newField(draft.analysis.fields);
                    update((d) => ({ ...d, analysis: { ...d.analysis, fields: [...d.analysis.fields, f] } }));
                    toggle(f.key, true);
                  }}
                >
                  Agregar dato
                </Button>
              )}
              <Button
                variant="default"
                size="xs"
                leftSection={<IconPlus size={16} />}
                onClick={() => {
                  const o = newOutcome(draft.analysis.outcomes);
                  const list = draft.analysis.outcomes;
                  // Antes del de por defecto, que queda ultimo.
                  update((d) => ({
                    ...d,
                    analysis: {
                      ...d.analysis,
                      outcomes: list.length ? [...list.slice(0, -1), o, ...list.slice(-1)] : [o],
                    },
                  }));
                  toggle(o.key, true);
                }}
              >
                Agregar resultado
              </Button>
            </Group>
          }
        >
          <Stack gap="md">
            {!external && (
              <>
                <Switch
                  label="Escribir un resumen de lo hablado"
                  description="Un párrafo para el detalle de la conversación, el email y las herramientas ({{call.summary}})."
                  checked={draft.analysis.summary}
                  onChange={(e) =>
                    update((d) => ({ ...d, analysis: { ...d.analysis, summary: e.currentTarget.checked } }))
                  }
                />
                {summaryError && (
                  <Text size="xs" c="red">
                    {summaryError}
                  </Text>
                )}
                <VariableField
                  label="Instrucciones para el análisis"
                  description="Qué mirar, qué ignorar y cómo resumir. Vacío: las instrucciones de la plataforma."
                  field="analysis"
                  declared={declared}
                  multiline
                  minRows={3}
                  maxRows={10}
                  value={draft.analysis.instructions}
                  onChange={(instructions) =>
                    update((d) => ({ ...d, analysis: { ...d.analysis, instructions } }))
                  }
                  error={errorAt(errors, 'analysis.instructions')}
                />
                <Stack gap="xs">
                  <Text size="sm" fw={600}>
                    Datos
                  </Text>
                  <Text size="xs" c="dimmed">
                    Se extraen en este orden. El nombre interno es la clave que usan los resultados y las
                    herramientas ({'{{fields.nombre}}'}).
                  </Text>
                  {draft.analysis.fields.map((f, i) => (
                    <FieldEditor
                      key={f.key}
                      field={f}
                      index={i}
                      draft={draft}
                      opened={opened.has(f.key)}
                      onToggle={() => toggle(f.key)}
                      update={update}
                      errors={errors}
                    />
                  ))}
                  {draft.analysis.fields.length === 0 && (
                    <Text size="xs" c="dimmed">
                      Sin datos: el análisis solo escribe el resumen.
                    </Text>
                  )}
                </Stack>
              </>
            )}
            <Stack gap="xs">
              <Text size="sm" fw={600}>
                Resultados
              </Text>
              <Text size="xs" c="dimmed">
                Valen el primero cuyas condiciones se cumplen; el último es el de por defecto.
              </Text>
              {draft.analysis.outcomes.map((o, i) => (
                <OutcomeEditor
                  key={o.key}
                  outcome={o}
                  index={i}
                  draft={draft}
                  opened={opened.has(o.key)}
                  onToggle={() => toggle(o.key)}
                  update={update}
                  errors={errors}
                />
              ))}
              {draft.analysis.outcomes.length === 0 && (
                <Text size="xs" c="dimmed">
                  Sin resultados: la conversación queda sin clasificar.
                </Text>
              )}
            </Stack>
          </Stack>
        </Section>
      </Stack>
    </PartContext.Provider>
  );
}

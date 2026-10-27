import {
  ActionIcon,
  Autocomplete,
  Badge,
  Button,
  Card,
  Collapse,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  TagsInput,
  Text,
  Textarea,
  TextInput,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { IconArrowDown, IconArrowUp, IconChevronDown, IconPlus, IconTrash } from '@tabler/icons-react';
import { createContext, type ReactNode, useContext } from 'react';
import type { FieldError } from '@/api/errors';
import { PlanGate } from '@/components/PlanGate';
import { useTools } from '@/features/tools/api';
import { VoiceSelect } from '@/features/voices/VoiceSelect';
import {
  type ConditionDraft,
  type ConditionValue,
  type Draft,
  FIELD_TYPES,
  type FieldDraft,
  hasPhoneField,
  type FieldType,
  move,
  newField,
  newKey,
  newOutcome,
  OPENING_DELAY_MS,
  type OutcomeDraft,
  type Part,
  renameField,
  renumber,
  type Requirement,
  SECTION_PART,
  sectionId,
  withPhoneField,
} from './draft';
import { ExternalSection } from './ExternalSection';
import { HandoffEditor } from './HandoffSection';
import { LlmSection } from './LlmSection';
import { SecretsSection } from './SecretsSection';
import { neededSecrets } from './grants';
import { ClientToolsEditor } from './ToolsSection';

const LANGUAGES = ['es-AR', 'es-UY', 'es-CL', 'es-MX', 'es-ES', 'en-US', 'pt-BR'];
const TYPE_LABEL: Record<string, string> = Object.fromEntries(FIELD_TYPES.map((t) => [t.value, t.label]));
const REQUIREMENT_LABEL: Record<Requirement, string> = {
  yes: 'Obligatorio',
  no: 'Opcional',
  if: 'Condicional',
};

/** La pestaña que se esta editando: cada seccion se muestra solo en la suya (SECTION_PART). */
const PartContext = createContext<Part>('conversacion');

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

// ---------- datos ----------

function FieldEditor({
  field,
  index,
  draft,
  opened,
  onToggle,
  update,
}: {
  field: FieldDraft;
  index: number;
  draft: Draft;
  opened: boolean;
  onToggle: () => void;
  update: (fn: (d: Draft) => Draft) => void;
}) {
  const count = draft.fields.length;
  const set = (patch: Partial<FieldDraft>) =>
    update((d) => ({ ...d, fields: d.fields.map((f, i) => (i === index ? { ...f, ...patch } : f)) }));
  const shift = (to: number) => update((d) => ({ ...d, fields: renumber(move(d.fields, index, to)) }));
  const others = draft.fields.filter((_, i) => i !== index);
  const usedBy =
    draft.fields.some((f) => f.conditions.some((c) => c.field === field.name)) ||
    draft.outcomes.some((o) => o.conditions.some((c) => c.field === field.name));

  return (
    <ItemBlock
      id={sectionId(`dato-${field.key}`)}
      opened={opened}
      onToggle={onToggle}
      summary={
        <Group gap="xs" wrap="wrap">
          <Text span className="mono" c="dimmed">
            {index + 1}
          </Text>
          <Text span fw={600}>
            {field.label || field.name || 'Sin nombre'}
          </Text>
          {field.label && (
            <Text span className="mono" c="dimmed">
              {field.name}
            </Text>
          )}
          <Badge color="gray">{TYPE_LABEL[field.type]}</Badge>
          <Badge color="gray">
            {field.requirement === 'if' && field.conditions.length
              ? `Si ${conditionsText(field.conditions, draft.fields)}`
              : REQUIREMENT_LABEL[field.requirement]}
          </Badge>
        </Group>
      }
      actions={
        <>
          <IconAction label="Subir" onClick={() => shift(index - 1)} disabled={index === 0}>
            <IconArrowUp size={18} />
          </IconAction>
          <IconAction label="Bajar" onClick={() => shift(index + 1)} disabled={index === count - 1}>
            <IconArrowDown size={18} />
          </IconAction>
          <IconAction
            label={count === 1 ? 'El agente necesita al menos un dato' : 'Quitar dato'}
            color="red"
            disabled={count === 1}
            onClick={() => update((d) => ({ ...d, fields: d.fields.filter((_, i) => i !== index) }))}
          >
            <IconTrash size={18} />
          </IconAction>
        </>
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
        />
        <Stack gap={4}>
          <Text size="sm" fw={600}>
            ¿Es obligatorio?
          </Text>
          <SegmentedControl
            fullWidth
            data={[
              { value: 'yes', label: 'Sí' },
              { value: 'no', label: 'No' },
              { value: 'if', label: 'Según otro dato' },
            ]}
            value={field.requirement}
            onChange={(v) => set({ requirement: v as Requirement })}
          />
        </Stack>
      </SimpleGrid>
      {field.type === 'choice' && (
        <TagsInput
          label="Opciones"
          description="Los valores posibles. Enter o coma para agregar cada una."
          placeholder="si, no, dudas"
          value={field.options}
          onChange={(options) => set({ options })}
          clearable
        />
      )}
      {field.requirement === 'if' && (
        <ConditionsEditor
          intro="Es obligatorio si se cumplen todas estas condiciones:"
          conditions={field.conditions}
          fields={others}
          onChange={(conditions) => set({ conditions })}
        />
      )}
      <Textarea
        label="Descripción"
        description='Qué es el dato y cómo se interpreta: la extracción la usa para sacar el valor. Si dice "No se pregunta", el agente lo toma solo si surge.'
        autosize
        minRows={2}
        maxRows={8}
        value={field.description}
        onChange={(e) => set({ description: e.currentTarget.value })}
      />
      <Textarea
        label="Pregunta sugerida"
        description="El agente la reformula para que la conversación sea natural."
        placeholder="¿Me pasás un teléfono para contactarte?"
        autosize
        minRows={1}
        maxRows={4}
        value={field.question}
        onChange={(e) => set({ question: e.currentTarget.value })}
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
}: {
  outcome: OutcomeDraft;
  index: number;
  draft: Draft;
  opened: boolean;
  onToggle: () => void;
  update: (fn: (d: Draft) => Draft) => void;
}) {
  const last = draft.outcomes.length - 1;
  const isDefault = index === last;
  // Con el agente del cliente no hay datos: el resultado lo elige su agente (end_call), no las condiciones.
  const external = draft.external !== null;
  const set = (patch: Partial<OutcomeDraft>) =>
    update((d) => ({ ...d, outcomes: d.outcomes.map((o, i) => (i === index ? { ...o, ...patch } : o)) }));
  // El ultimo (por defecto) queda fijo al final.
  const shift = (to: number) => update((d) => ({ ...d, outcomes: move(d.outcomes, index, to) }));

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
                  ? `Si ${conditionsText(outcome.conditions, draft.fields)}`
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
              onClick={() => update((d) => ({ ...d, outcomes: d.outcomes.filter((_, i) => i !== index) }))}
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
          onChange={(e) => set({ id: e.currentTarget.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
        />
      </SimpleGrid>
      <Switch
        label="Cumple el objetivo"
        description="Cuenta como éxito en las métricas. Si faltan datos obligatorios, la conversación queda como incompleta."
        checked={outcome.goal}
        onChange={(e) => set({ goal: e.currentTarget.checked })}
      />
      <Switch
        label="No volver a llamar"
        description="En una campaña de llamadas, el teléfono pasa a la lista de bajas de voz del cliente y ninguna campaña lo vuelve a llamar."
        checked={outcome.noContact}
        onChange={(e) => set({ noContact: e.currentTarget.checked })}
      />
      <Textarea
        label="Mensaje de cierre"
        description="Guía para la despedida: el agente la adapta."
        autosize
        minRows={2}
        maxRows={6}
        value={outcome.message}
        onChange={(e) => set({ message: e.currentTarget.value })}
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
          fields={draft.fields}
          onChange={(conditions) => set({ conditions })}
        />
      )}
    </ItemBlock>
  );
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
  /** Errores del servidor con su ruta, para mostrarlos en el campo (por ahora, los de la derivación). */
  errors?: FieldError[];
  /** El agente ya guardado: sus secretos se cargan aparte de la definición. */
  agentId?: string;
}) {
  const set = (patch: Partial<Draft>) => update((d) => ({ ...d, ...patch }));
  // Con el agente del cliente, el prompt, el modelo y los datos son suyos: esas secciones no aplican.
  const external = draft.external !== null;
  const clientTools = useTools(external ? undefined : clientId);

  return (
    <PartContext.Provider value={part}>
      <Stack gap="md">
        <Section
          name="agente"
          title="Agente"
          description={
            external
              ? 'Quién es. Con tu propio agente, cómo responde lo decide tu agente.'
              : 'Quién es y cómo responde. El prompt se arma de estos campos.'
          }
        >
          <Stack gap="sm">
            <SimpleGrid cols={{ base: 1, sm: 3 }}>
              <TextInput
                label="Nombre"
                description="Cómo se presenta."
                placeholder="Sofía"
                value={draft.name}
                onChange={(e) => set({ name: e.currentTarget.value })}
              />
              <TextInput
                label="Rol"
                description="Quién es y para quién trabaja."
                placeholder="recepcionista virtual de la Clínica del Sol"
                value={draft.role}
                onChange={(e) => set({ role: e.currentTarget.value })}
              />
              <Autocomplete
                label="Idioma"
                description="Código, como es-AR."
                data={LANGUAGES}
                value={draft.language}
                onChange={(language) => set({ language })}
              />
            </SimpleGrid>
          </Stack>
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
          description="Con la que habla en las llamadas y las notas de voz. Elegila y escuchala acá mismo. Abajo, cómo arranca y qué guarda de cada conversación."
        >
          <Stack gap="sm">
            <VoiceSelect
              key={voiceSeed}
              value={draft.voice}
              onChange={(voice) => set({ voice })}
              previewText={draft.opening}
            />
            <Switch
              label="Pregenerar el audio de la apertura"
              description="En las llamadas, la apertura se sintetiza entera al guardar (suena más natural que frase por frase) y se reproduce ese audio. Se regenera en cada guardado. No aplica si la apertura tiene {{variables}} o la llamada usa otra voz."
              checked={draft.openingAudio}
              onChange={(e) => set({ openingAudio: e.currentTarget.checked })}
            />
            <NumberInput
              label="Espera antes de la apertura (ms)"
              description="En las llamadas, cuánto espera desde que se conecta hasta que empieza a hablar."
              value={draft.openingDelayMs}
              onChange={(v) => set({ openingDelayMs: typeof v === 'number' ? v : OPENING_DELAY_MS })}
              min={0}
              max={10_000}
              step={100}
              allowDecimal={false}
              maw={260}
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
                  Al cortar, Atentina le manda al cliente los datos, el resultado y la conversación. El
                  cliente lo apaga o elige a quién le llega en Mi cuenta.
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
                          : 'Falta un dato de tipo Teléfono: en las llamadas por el link el email va a ir sin teléfono.'}
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

        {!external && (
          <Section
            name="modelo"
            title="Modelo de lenguaje"
            description="Qué modelo contesta y con qué parámetros."
          >
            <LlmSection draft={draft} update={update} clientId={clientId} />
          </Section>
        )}

        <Section name="objetivo" title="Objetivo y apertura">
          <Stack gap="sm">
            <Textarea
              label="Objetivo"
              description="Qué tiene que lograr en la conversación."
              autosize
              minRows={2}
              maxRows={8}
              value={draft.objective}
              onChange={(e) => set({ objective: e.currentTarget.value })}
            />
            <Textarea
              label="Apertura"
              description="Lo primero que dice al atender o al llamar. Por WhatsApp es la guía del saludo."
              autosize
              minRows={2}
              maxRows={6}
              value={draft.opening}
              onChange={(e) => set({ opening: e.currentTarget.value })}
            />
          </Stack>
        </Section>

        {!external && (
          <Section
            name="reglas"
            title="Reglas"
            description="Tono, límites y formato de las respuestas, una por regla. Las de cada canal (voz o WhatsApp) se suman solas."
          >
            <Stack gap="xs">
              {draft.rules.map((r, i) => (
                <Group key={r.key} gap="xs" align="flex-start" wrap="nowrap">
                  <Text className="mono" c="dimmed" pt={8} w={20} ta="right">
                    {i + 1}
                  </Text>
                  <Textarea
                    aria-label={`Regla ${i + 1}`}
                    autosize
                    minRows={1}
                    maxRows={6}
                    style={{ flex: 1 }}
                    value={r.text}
                    onChange={(e) => {
                      const text = e.currentTarget.value;
                      update((d) => ({ ...d, rules: d.rules.map((x, j) => (j === i ? { ...x, text } : x)) }));
                    }}
                  />
                  <IconAction
                    label="Quitar regla"
                    color="red"
                    onClick={() => update((d) => ({ ...d, rules: d.rules.filter((_, j) => j !== i) }))}
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
                onClick={() => update((d) => ({ ...d, rules: [...d.rules, { key: newKey(), text: '' }] }))}
              >
                Agregar regla
              </Button>
            </Stack>
          </Section>
        )}

        {!external && (
          <Section
            name="conocimiento"
            title="Base de conocimiento"
            description="Lo único que el agente sabe del negocio: productos, precios, horarios, direcciones, preguntas frecuentes. Lo que no esté acá, no lo responde."
          >
            <Textarea
              aria-label="Base de conocimiento"
              autosize
              minRows={6}
              maxRows={24}
              placeholder="- Horarios: de lunes a viernes de nueve a dieciocho."
              value={draft.knowledge}
              onChange={(e) => set({ knowledge: e.currentTarget.value })}
            />
          </Section>
        )}

        {!external && (
          <Section
            name="datos"
            title="Datos a obtener"
            description="Lo que el agente pregunta, en este orden salvo que la persona los dé antes. La conversación termina cuando tiene los obligatorios."
            actions={
              <Button
                variant="default"
                size="xs"
                leftSection={<IconPlus size={16} />}
                onClick={() => {
                  const f = newField(draft.fields);
                  update((d) => ({ ...d, fields: [...d.fields, f] }));
                  toggle(f.key, true);
                }}
              >
                Agregar dato
              </Button>
            }
          >
            <Stack gap="xs">
              {draft.fields.map((f, i) => (
                <FieldEditor
                  key={f.key}
                  field={f}
                  index={i}
                  draft={draft}
                  opened={opened.has(f.key)}
                  onToggle={() => toggle(f.key)}
                  update={update}
                />
              ))}
            </Stack>
          </Section>
        )}

        <Section
          name="resultados"
          title="Resultados"
          description={
            external
              ? 'Clasifican la conversación al terminar: tu agente elige uno al llamar a end_call (por su ID). Si no elige, vale el último.'
              : 'Clasifican la conversación al terminar: vale el primero cuyas condiciones se cumplen. El último es el de por defecto.'
          }
          actions={
            <Button
              variant="default"
              size="xs"
              leftSection={<IconPlus size={16} />}
              onClick={() => {
                const o = newOutcome(draft.outcomes);
                // Antes del de por defecto, que queda ultimo.
                update((d) => ({ ...d, outcomes: [...d.outcomes.slice(0, -1), o, ...d.outcomes.slice(-1)] }));
                toggle(o.key, true);
              }}
            >
              Agregar resultado
            </Button>
          }
        >
          <Stack gap="xs">
            {draft.outcomes.map((o, i) => (
              <OutcomeEditor
                key={o.key}
                outcome={o}
                index={i}
                draft={draft}
                opened={opened.has(o.key)}
                onToggle={() => toggle(o.key)}
                update={update}
              />
            ))}
          </Stack>
        </Section>
      </Stack>
    </PartContext.Provider>
  );
}

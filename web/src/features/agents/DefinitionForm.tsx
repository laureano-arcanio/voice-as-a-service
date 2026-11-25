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
  Textarea,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { IconChevronDown, IconPlus, IconTrash } from '@tabler/icons-react';
import { createContext, type ReactNode, useContext } from 'react';
import type { FieldError } from '@/api/errors';
import { PlanGate } from '@/components/PlanGate';
import { PromptEditor, VariableField, type ExtraVariable } from '@/components/variables';
import { useTools } from '@/features/tools/api';
import { useAreas } from '@/features/team/api';
import { VoiceSelect } from '@/features/voices/VoiceSelect';
import {
  type Draft,
  FIELD_TYPES,
  type FieldDraft,
  FIRST_MESSAGE_DELAY_MS,
  type FieldType,
  MAX_FIRST_MESSAGE,
  MAX_PROMPT,
  newField,
  type Part,
  renameField,
  SECTION_PART,
  sectionId,
  TURN_ATTENTION_DEFAULTS,
  type TurnAttentionDraft,
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

/** Los errores de una ruta con sus hijos (`analysis.summary.`). */
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

/** Bloque plegable de un dato del análisis: un bloque de 12 px de radio dentro de la tarjeta. */
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
          description="Clave del dato: minúsculas, números y _."
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

/** Las variables declaradas, como las reciben los editores de texto. */
function declaredOf(draft: Draft) {
  return draft.variables
    .filter((v) => v.name.trim())
    .map((v) => ({ name: v.name.trim(), description: v.description }));
}

// ---------- si la persona no responde ----------

/** Atencion del turno en llamadas (draft.turnAttention): avisos si la persona queda en silencio y
 * cierre con aviso. Los tiempos en segundos; la definicion los guarda en ms (draft.ts). */
function TurnAttentionEditor({
  draft,
  update,
  errors,
  areaNames,
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  /** Errores del servidor (guardado), con su ruta: van en cada campo. */
  errors: FieldError[];
  /** id → nombre de las areas del cliente; las del agente estan en draft.handoff. */
  areaNames: Map<string, string>;
}) {
  const att = draft.turnAttention;
  const set = (patch: Partial<TurnAttentionDraft>) =>
    update((d) => ({ ...d, turnAttention: { ...d.turnAttention, ...patch } }));
  // Al vaciar un numero vuelve al default (no hay valor vacio en la definicion).
  const num = (v: string | number, d: number) => (typeof v === 'number' ? v : d);
  // Las areas a las que el agente ya puede derivar; el nombre si ya cargo la lista del cliente.
  const areaOptions = draft.handoff.areas.map((a) => ({
    value: a.areaId,
    label: areaNames.get(a.areaId) ?? a.areaId,
  }));
  // Un area elegida que ya no esta en handoff queda visible (el servidor la rechaza al guardar).
  if (att.onEndAreaId && !areaOptions.some((o) => o.value === att.onEndAreaId))
    areaOptions.push({
      value: att.onEndAreaId,
      label: areaNames.get(att.onEndAreaId) ?? att.onEndAreaId,
    });

  return (
    <Stack gap="sm">
      <Switch
        label="Activar"
        description="Si la persona queda en silencio después de una respuesta del agente: repite la última pregunta, avisa de nuevo y después cierra la llamada con un aviso. Solo en llamadas; por WhatsApp no aplica."
        checked={att.enabled}
        onChange={(e) => set({ enabled: e.currentTarget.checked })}
      />
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <NumberInput
          label="Repetir la última pregunta a los (segundos)"
          description="De silencio desde que el agente deja de hablar."
          value={att.reminderAfterS}
          onChange={(v) => set({ reminderAfterS: num(v, TURN_ATTENTION_DEFAULTS.reminderAfterS) })}
          min={3}
          max={30}
          allowDecimal={false}
          error={errorAt(errors, 'turn_attention.reminder_after_ms')}
        />
        <NumberInput
          label="Cantidad de avisos"
          description="Cuántas veces avisa antes del cierre. 0 = solo el cierre."
          value={att.reminderMax}
          onChange={(v) => set({ reminderMax: num(v, TURN_ATTENTION_DEFAULTS.reminderMax) })}
          min={0}
          max={5}
          allowDecimal={false}
          error={errorAt(errors, 'turn_attention.reminder_max')}
        />
        <NumberInput
          label="Espera entre avisos (segundos)"
          description="Entre un aviso y el siguiente."
          value={att.reminderGapS}
          onChange={(v) => set({ reminderGapS: num(v, TURN_ATTENTION_DEFAULTS.reminderGapS) })}
          min={3}
          max={30}
          allowDecimal={false}
          error={errorAt(errors, 'turn_attention.reminder_gap_ms')}
        />
        <NumberInput
          label="Cerrar la llamada a los (segundos)"
          description="Silencio total desde la última respuesta del agente; después hace lo que dice Al cerrar."
          value={att.endAfterS}
          onChange={(v) => set({ endAfterS: num(v, TURN_ATTENTION_DEFAULTS.endAfterS) })}
          min={15}
          max={120}
          allowDecimal={false}
          error={errorAt(errors, 'turn_attention.end_after_ms')}
        />
      </SimpleGrid>
      <Group gap="sm" align="flex-end" wrap="wrap">
        <Select
          label="Al cerrar"
          description="Qué hace el agente cuando se cumple el tiempo de cierre."
          data={[
            { value: 'hang_up', label: 'Cortar' },
            { value: 'transfer', label: 'Pasar con una persona' },
          ]}
          value={att.onEnd}
          onChange={(v) => v && set({ onEnd: v as 'hang_up' | 'transfer' })}
          allowDeselect={false}
          error={errorAt(errors, 'turn_attention.on_end')}
          maw={360}
        />
        {att.onEnd === 'transfer' && (
          <Select
            label="Pasar al área"
            description="Solo las áreas que el agente ya puede derivar. Vacío = la primera."
            placeholder="La primera área"
            data={areaOptions}
            value={att.onEndAreaId || null}
            onChange={(v) => set({ onEndAreaId: v ?? '' })}
            clearable
            error={errorAt(errors, 'turn_attention.on_end_area_id')}
            maw={360}
          />
        )}
      </Group>
      {att.onEnd === 'transfer' && draft.handoff.areas.length === 0 && (
        <Text size="xs" c="orange.8">
          Este agente no tiene áreas de derivación: marcá al menos una en Derivación a personas
          (pestaña Herramientas), o el cierre no va a poder pasar con una persona.
        </Text>
      )}
      <Textarea
        label="Texto del primer aviso"
        description="Lo que dice al primer aviso, antes de repetir la última pregunta. Vacío = el texto de la plataforma."
        placeholder="¿Me escuchás? Te repito:"
        autosize
        minRows={1}
        maxRows={3}
        maxLength={300}
        value={att.reminderText}
        error={errorAt(errors, 'turn_attention.reminder_text')}
        onChange={(e) => set({ reminderText: e.currentTarget.value })}
      />
      <Textarea
        label="Texto del cierre"
        description="Lo que dice antes de cerrar la llamada. Vacío = el texto de la plataforma."
        placeholder="No te escucho bien. Podés volver a llamarnos o escribirnos por WhatsApp. ¡Gracias!"
        autosize
        minRows={1}
        maxRows={3}
        maxLength={300}
        value={att.endText}
        error={errorAt(errors, 'turn_attention.end_text')}
        onChange={(e) => set({ endText: e.currentTarget.value })}
      />
      <Switch
        label="Repetir cuando pide ¿cómo? o dice que no escuchó"
        description="El agente repite su última respuesta tal cual, sin volver a empezar."
        checked={att.repeatLastReply}
        onChange={(e) => set({ repeatLastReply: e.currentTarget.checked })}
      />
      <Switch
        label="Pedir que repita si no se entiende lo que dijo"
        description="Si la persona habló pero no se pudo transcribir, el agente se lo pide (espera 3 s)."
        checked={att.sttRetry}
        onChange={(e) => set({ sttRetry: e.currentTarget.checked })}
      />
    </Stack>
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
  /** Claves de los datos desplegados. */
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
  // Nombres de las areas del cliente: el area del cierre de turn_attention los usa.
  const areas = useAreas(clientId);
  const areaNames = new Map((areas.data ?? []).map((a) => [a.id, a.name]));
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
          name="sin_respuesta"
          title="Si la persona no responde"
          description="En las llamadas: qué hace el agente si la persona queda en silencio. Repite la última pregunta, avisa de nuevo y cierra la llamada con un aviso. Apagado, un silencio largo deja la llamada muda hasta que corta quien llamó."
        >
          <TurnAttentionEditor draft={draft} update={update} errors={errors} areaNames={areaNames} />
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
              ? 'Con tu propio agente el análisis lo hace él: Atentina no extrae datos ni resumen.'
              : 'Una llamada guiada al terminar saca los datos y el resumen. Sin esto, el agente no extrae nada.'
          }
          actions={
            !external && (
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
            )
          }
        >
          {external ? (
            <Text size="sm" c="dimmed">
              El análisis es de tu agente: cerrás la llamada con end_call y los datos que tu endpoint registre
              quedan de tu lado.
            </Text>
          ) : (
            <Stack gap="md">
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
                  Se extraen en este orden. El nombre interno es la clave que usan las herramientas
                  ({'{{fields.nombre}}'}).
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
            </Stack>
          )}
        </Section>
      </Stack>
    </PartContext.Provider>
  );
}

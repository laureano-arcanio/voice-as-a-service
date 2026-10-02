import {
  ActionIcon,
  Autocomplete,
  Badge,
  Button,
  Card,
  Collapse,
  Group,
  NumberInput,
  Radio,
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
import type { ReactNode } from 'react';
import { VoiceSelect } from '@/features/voices/VoiceSelect';
import {
  type ConditionDraft,
  type ConditionValue,
  type Draft,
  type Engine,
  FIELD_TYPES,
  type FieldDraft,
  type FieldType,
  move,
  newField,
  newKey,
  newOutcome,
  type OutcomeDraft,
  renameField,
  renumber,
  type Requirement,
  sectionId,
} from './draft';
import { EngineCards } from './EngineCards';

const LANGUAGES = ['es-AR', 'es-UY', 'es-CL', 'es-MX', 'es-ES', 'en-US', 'pt-BR'];
const TYPE_LABEL: Record<string, string> = Object.fromEntries(FIELD_TYPES.map((t) => [t.value, t.label]));
const REQUIREMENT_LABEL: Record<Requirement, string> = {
  yes: 'Obligatorio',
  no: 'Opcional',
  if: 'Condicional',
};

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
          data={FIELD_TYPES.map((t) => ({ value: t.value, label: t.label }))}
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
              ? 'En cualquier otro caso'
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
      <Textarea
        label="Mensaje de cierre"
        description="Guía para la despedida: el agente la adapta."
        autosize
        minRows={2}
        maxRows={6}
        value={outcome.message}
        onChange={(e) => set({ message: e.currentTarget.value })}
      />
      {isDefault ? (
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
  draft,
  update,
  opened,
  toggle,
  voiceSeed,
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
  /** Claves de los datos y resultados desplegados. */
  opened: Set<string>;
  toggle: (key: string, open?: boolean) => void;
  /** Para reiniciar el texto de la prueba de voz al cambiar de agente. */
  voiceSeed: string;
}) {
  const set = (patch: Partial<Draft>) => update((d) => ({ ...d, ...patch }));

  return (
    <Stack gap="md">
      <Section
        name="agente"
        title="Agente"
        description="Quién es y cómo responde. El prompt se arma de estos campos."
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
          <Radio.Group
            label="Motor"
            description="La definición es la misma con los dos: cambiarlo no toca nada más."
            value={draft.engine}
            onChange={(v) => set({ engine: v as Engine })}
          >
            <EngineCards />
          </Radio.Group>
        </Stack>
      </Section>

      <Section
        name="voz"
        title="Voz"
        description="Con la que habla en las llamadas y las notas de voz. Elegila y escuchala acá mismo."
      >
        <VoiceSelect
          key={voiceSeed}
          value={draft.voice}
          onChange={(voice) => set({ voice })}
          previewText={draft.opening}
        />
      </Section>

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

      <Section
        name="reglas"
        title="Reglas"
        description="Tono, límites y formato de las respuestas, una por regla. Las de cada canal (voz o WhatsApp) las suma el motor."
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

      <Section
        name="resultados"
        title="Resultados"
        description="Clasifican la conversación al terminar: vale el primero cuyas condiciones se cumplen. El último es el de por defecto."
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
  );
}

import {
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  PasswordInput,
  Select,
  Stack,
  Switch,
  TagsInput,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { IconPlayerPlay } from '@tabler/icons-react';
import { useState } from 'react';
import type { ToolTestResult, ToolType } from '@/api/types';
import { ErrorAlert } from '@/components/QueryState';
import { useAgents } from '@/features/agents/api';
import { prettyJson } from '@/lib/format';
import { useTestToolDraft } from './api';
import { type Json, llmParameters } from './draft';

const obj = (x: unknown): Json => (x && typeof x === 'object' && !Array.isArray(x) ? (x as Json) : {});

/** Un argumento como lo mandaria el agente, desde el campo del formulario. */
function argValue(schema: Json, raw: unknown): unknown {
  if (raw === undefined || raw === '') return undefined;
  if (schema.type === 'object' && typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch {
      return raw;
    }
  }
  return raw;
}

function ArgInput({
  name,
  schema,
  required,
  value,
  onChange,
}: {
  name: string;
  schema: Json;
  required: boolean;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const label = (
    <span className="mono">
      {name}
      {required ? ' *' : ''}
    </span>
  );
  const description = typeof schema.description === 'string' ? schema.description : undefined;
  const options = Array.isArray(schema.enum) ? schema.enum.map(String) : null;
  if (schema.type === 'boolean')
    return (
      <Switch
        label={label}
        description={description}
        checked={value === true}
        onChange={(e) => onChange(e.currentTarget.checked)}
      />
    );
  if (options)
    return (
      <Select
        label={label}
        description={description}
        data={options}
        value={value == null ? null : String(value)}
        onChange={(v) =>
          onChange(
            v == null ? undefined : schema.type === 'string' || Number.isNaN(Number(v)) ? v : Number(v),
          )
        }
        clearable
      />
    );
  if (schema.type === 'integer' || schema.type === 'number')
    return (
      <NumberInput
        label={label}
        description={description}
        allowDecimal={schema.type === 'number'}
        value={typeof value === 'number' ? value : ''}
        onChange={(v) => onChange(typeof v === 'number' ? v : undefined)}
      />
    );
  if (schema.type === 'array')
    return (
      <TagsInput
        label={label}
        description={description}
        placeholder="Enter para agregar"
        value={Array.isArray(value) ? value.map(String) : []}
        onChange={onChange}
      />
    );
  if (schema.type === 'object')
    return (
      <Textarea
        label={label}
        description={description ?? 'En JSON.'}
        classNames={{ input: 'mono' }}
        autosize
        minRows={2}
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.currentTarget.value)}
      />
    );
  return (
    <TextInput
      label={label}
      description={description}
      value={typeof value === 'string' ? value : ''}
      onChange={(e) => onChange(e.currentTarget.value)}
    />
  );
}

function Block({ title, children }: { title: string; children: string }) {
  return (
    <div>
      <Text className="label" mb={4}>
        {title}
      </Text>
      <pre className="code" style={{ maxHeight: 280, overflow: 'auto', margin: 0 }}>
        {children}
      </pre>
    </div>
  );
}

export function TestResult({ result }: { result: ToolTestResult }) {
  return (
    <Stack gap="sm" aria-label="Resultado de la prueba">
      <Group gap="xs">
        <Badge color={result.ok ? 'green' : 'red'}>{result.ok ? 'Funcionó' : 'Falló'}</Badge>
        {result.status != null && (
          <Text span className="mono" size="sm">
            HTTP {result.status}
          </Text>
        )}
        <Text span className="mono" size="sm" c="dimmed">
          {result.ms} ms
        </Text>
      </Group>
      {result.error && (
        <Text size="sm" c="red.7">
          {result.error}
        </Text>
      )}
      {result.request && <Block title="Request enviado">{prettyJson(result.request)}</Block>}
      {result.data !== undefined && result.data !== null && (
        <Block title="Respuesta">{prettyJson(result.data)}</Block>
      )}
      <Block title="Lo que recibe el agente">{prettyJson(result.llm)}</Block>
      {result.logs.length > 0 && <Block title="Logs">{result.logs.join('\n')}</Block>}
      {Object.keys(result.assigned ?? {}).length > 0 && (
        <Block title="Guardado en variables">{prettyJson(result.assigned)}</Block>
      )}
    </Stack>
  );
}

/** Probar la herramienta como esta en el editor (sin guardar): la ejecuta de verdad. */
export function ToolTestPanel({
  clientId,
  type,
  definition,
  secrets,
  disabled,
}: {
  clientId: string;
  type: ToolType;
  definition: Json;
  /** Los secretos que pide la herramienta. */
  secrets: string[];
  disabled?: string;
}) {
  const schema = llmParameters(type, definition);
  const props = Object.entries(obj(schema.properties)).map(([k, v]) => [k, obj(v)] as const);
  const required = new Set(Array.isArray(schema.required) ? schema.required.map(String) : []);
  const [args, setArgs] = useState<Json>({});
  const [agentId, setAgentId] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [from, setFrom] = useState('');
  const agents = useAgents(clientId);
  const test = useTestToolDraft(clientId);

  const run = () => {
    const sent: Json = {};
    for (const [name, s] of props) {
      const v = argValue(s, args[name]);
      if (v !== undefined) sent[name] = v;
    }
    const adhoc = Object.fromEntries(Object.entries(values).filter(([k, v]) => v && secrets.includes(k)));
    test.mutate({
      type,
      definition,
      args: sent,
      agent_id: agentId,
      secrets: Object.keys(adhoc).length ? adhoc : null,
      call: from.trim() ? { from: from.trim(), channel: 'voice', mode: 'inbound' } : null,
    });
  };

  return (
    <Card>
      <Title order={4} mb={4}>
        Probar
      </Title>
      <Text size="xs" c="dimmed" mb="sm">
        La ejecuta de verdad, como la tenés en el editor (sin guardar): si cambia algo en tu sistema, lo
        cambia.
      </Text>
      <Stack gap="sm">
        {props.length === 0 ? (
          <Text size="sm" c="dimmed">
            Sin argumentos: el agente la llama sin datos.
          </Text>
        ) : (
          props.map(([name, s]) => (
            <ArgInput
              key={name}
              name={name}
              schema={s}
              required={required.has(name)}
              value={args[name]}
              onChange={(v) => setArgs((a) => ({ ...a, [name]: v }))}
            />
          ))
        )}
        {secrets.length > 0 && (
          <>
            <Text size="xs" c="dimmed">
              Usa los secretos cargados en Secretos (los del cliente).
            </Text>
            <Select
              label="Con los valores propios de un agente (opcional)"
              description="Si un agente usa otro valor para algún secreto, elegilo para probar con ese."
              placeholder="Ninguno"
              data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
              value={agentId}
              onChange={setAgentId}
              clearable
              searchable
            />
            <Text size="xs" c="dimmed">
              O escribí valores solo para esta prueba (no se guardan; pisan a los cargados):
            </Text>
            {secrets.map((s) => (
              <PasswordInput
                key={s}
                label={<span className="mono">{s}</span>}
                value={values[s] ?? ''}
                onChange={(e) => {
                  const v = e.currentTarget.value;
                  setValues((x) => ({ ...x, [s]: v }));
                }}
                autoComplete="off"
              />
            ))}
          </>
        )}
        <TextInput
          label="Número de quien llama (ejemplo)"
          description="Para {{call.from}}."
          placeholder="+5493511234567"
          value={from}
          onChange={(e) => setFrom(e.currentTarget.value)}
        />
        <Button
          leftSection={<IconPlayerPlay size={16} />}
          variant="default"
          onClick={run}
          loading={test.isPending}
          disabled={!!disabled}
          title={disabled}
          style={{ alignSelf: 'flex-start' }}
        >
          Probar herramienta
        </Button>
        {disabled && (
          <Text size="xs" c="dimmed">
            {disabled}
          </Text>
        )}
        {test.isError && <ErrorAlert error={test.error} title="No se pudo probar" />}
        {test.data && <TestResult result={test.data} />}
      </Stack>
    </Card>
  );
}

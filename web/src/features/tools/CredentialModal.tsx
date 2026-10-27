import {
  Autocomplete,
  Button,
  Group,
  Modal,
  PasswordInput,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useState } from 'react';
import type { Credential } from '@/api/types';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useClientSecrets, useCreateCredential, useUpdateCredential } from './api';
import { CREDENTIAL_VALUE, slugify } from './credentials';
import { AUTH_TYPES, cleanAuth, type CredentialType, type Json, SECRET_RE } from './draft';

const SLUG_RE = /^[a-z][a-z0-9_]{1,63}$/;

/**
 * Crear o cambiar una credencial: la autenticacion de una API (tipo y datos) con su valor, que se guarda en un
 * secreto del cliente. onSaved: el slug (para elegirla en la herramienta).
 */
export function CredentialModal({
  clientId,
  credential,
  onClose,
  onSaved,
}: {
  clientId: string;
  /** La que se cambia; sin ella, una nueva. */
  credential?: Credential;
  onClose: () => void;
  onSaved?: (slug: string) => void;
}) {
  const secrets = useClientSecrets(clientId);
  const create = useCreateCredential(clientId);
  const update = useUpdateCredential(clientId);
  const editing = !!credential;
  const initial = (credential?.auth ?? { type: 'bearer' }) as Json;
  const [name, setName] = useState(credential?.name ?? '');
  const [slug, setSlug] = useState(credential?.slug ?? '');
  const [slugTouched, setSlugTouched] = useState(editing);
  const [auth, setAuth] = useState<Json>(initial);
  const [secretTouched, setSecretTouched] = useState(editing);
  const [value, setValue] = useState('');
  const [description, setDescription] = useState(credential?.description ?? '');
  const [submitted, setSubmitted] = useState(false);

  const type = (auth.type as CredentialType) || 'bearer';
  const v = (k: string) => (typeof auth[k] === 'string' ? (auth[k] as string) : '');
  const set = (k: string, x: string) => setAuth((a) => ({ ...a, [k]: x }));
  const effectiveSlug = slugTouched ? slug : slugify(name);
  const suggested = `${(effectiveSlug || 'API').toUpperCase()}_${CREDENTIAL_VALUE[type].suffix}`.slice(0, 64);
  const secret = secretTouched ? v('secret') : suggested;
  const existing = (secrets.data ?? []).filter((s) => !s.missing);
  const secretExists = existing.some((s) => s.name === secret);
  const needsValue = !secretExists;

  const errors = {
    name: !name.trim() ? 'Escribí un nombre' : null,
    slug: SLUG_RE.test(effectiveSlug) ? null : 'Minúsculas, números y _ (ej. api_crm)',
    secret: SECRET_RE.test(secret) ? null : 'Mayúsculas, números y _ (ej. CRM_TOKEN)',
    value: needsValue && !value ? 'Escribí el valor' : null,
    token_url: type === 'oauth2_client_credentials' && !v('token_url') ? 'Obligatoria' : null,
    client_id: type === 'oauth2_client_credentials' && !v('client_id') ? 'Obligatorio' : null,
    username: type === 'basic' && !v('username') ? 'Obligatorio' : null,
    api_name: type === 'api_key' && !v('name') ? 'Obligatorio' : null,
  };
  const err = (k: keyof typeof errors) => (submitted ? errors[k] : null);

  const save = () => {
    setSubmitted(true);
    if (Object.values(errors).some(Boolean)) return;
    const body = {
      name: name.trim(),
      description: description.trim(),
      auth: cleanAuth({ ...auth, type, secret }),
      value: value || null,
    };
    const done = {
      onSuccess: () => {
        notifySuccess(editing ? 'Credencial guardada.' : 'Credencial creada.');
        onSaved?.(effectiveSlug);
        onClose();
      },
      onError: (e: unknown) => notifyError(e, 'No se pudo guardar'),
    };
    if (editing) update.mutate({ slug: credential.slug, body }, done);
    else create.mutate({ ...body, slug: effectiveSlug }, done);
  };

  return (
    <Modal
      opened
      onClose={onClose}
      title={editing ? `Credencial ${credential.name}` : 'Nueva credencial'}
      size="lg"
    >
      <Stack>
        <Text size="xs" c="dimmed">
          Cómo se identifica Atentina ante una API tuya. Se carga una vez y la usan todas las herramientas que
          llaman a esa API. El valor se guarda cifrado y el agente nunca lo ve.
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput
            label="Nombre"
            placeholder="API del CRM"
            data-autofocus
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            error={err('name')}
            maxLength={120}
          />
          <TextInput
            label="Identificador"
            description={editing ? 'No se puede cambiar.' : 'Se arma solo con el nombre.'}
            classNames={{ input: 'mono' }}
            value={effectiveSlug}
            readOnly={editing}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.currentTarget.value.toLowerCase());
            }}
            error={err('slug')}
          />
        </SimpleGrid>
        <Select
          label="Tipo"
          data={AUTH_TYPES}
          value={type}
          allowDeselect={false}
          onChange={(t) => t && setAuth((a) => ({ ...a, type: t }))}
        />
        {type === 'bearer' && (
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label="Header"
              placeholder="Authorization"
              value={v('header')}
              onChange={(e) => set('header', e.currentTarget.value)}
            />
            <TextInput
              label="Prefijo"
              placeholder="Bearer "
              value={v('prefix')}
              onChange={(e) => set('prefix', e.currentTarget.value)}
            />
          </SimpleGrid>
        )}
        {type === 'api_key' && (
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label="Nombre de la key"
              description="Del header o del parámetro."
              placeholder="X-API-Key"
              value={v('name')}
              onChange={(e) => set('name', e.currentTarget.value)}
              error={err('api_name')}
            />
            <Select
              label="Va en"
              description="Dónde se manda la key."
              data={[
                { value: 'header', label: 'Un header' },
                { value: 'query', label: 'La query' },
              ]}
              value={v('in') || 'header'}
              allowDeselect={false}
              onChange={(x) => x && set('in', x)}
            />
          </SimpleGrid>
        )}
        {type === 'basic' && (
          <TextInput
            label="Usuario"
            placeholder="atentina"
            value={v('username')}
            onChange={(e) => set('username', e.currentTarget.value)}
            error={err('username')}
          />
        )}
        {type === 'oauth2_client_credentials' && (
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label="URL del token"
              placeholder="https://auth.ejemplo.com/oauth/token"
              value={v('token_url')}
              onChange={(e) => set('token_url', e.currentTarget.value)}
              error={err('token_url')}
            />
            <TextInput
              label="Client ID"
              value={v('client_id')}
              onChange={(e) => set('client_id', e.currentTarget.value)}
              error={err('client_id')}
            />
            <TextInput
              label="Scope"
              value={v('scope')}
              onChange={(e) => set('scope', e.currentTarget.value)}
            />
            <TextInput
              label="Audience"
              value={v('audience')}
              onChange={(e) => set('audience', e.currentTarget.value)}
            />
            <Select
              label="Cómo se manda el client secret"
              data={[
                { value: 'body', label: 'En el body' },
                { value: 'basic', label: 'Con Basic' },
              ]}
              value={v('client_auth') || 'body'}
              allowDeselect={false}
              onChange={(x) => x && set('client_auth', x)}
            />
          </SimpleGrid>
        )}
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <PasswordInput
            label={CREDENTIAL_VALUE[type].label}
            description={
              secretExists
                ? 'Ya está cargado: dejalo vacío para mantenerlo.'
                : 'Se guarda cifrado; no se vuelve a mostrar.'
            }
            autoComplete="off"
            value={value}
            onChange={(e) => setValue(e.currentTarget.value)}
            error={err('value')}
          />
          <Autocomplete
            label="Se guarda en el secreto"
            description="Uno nuevo o uno que ya cargaste."
            classNames={{ input: 'mono' }}
            data={existing.map((s) => s.name)}
            value={secret}
            onChange={(x) => {
              setSecretTouched(true);
              set('secret', x.toUpperCase());
            }}
            error={err('secret')}
          />
        </SimpleGrid>
        <TextInput
          label="Descripción"
          placeholder="Usuario de integración del CRM"
          maxLength={255}
          value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={save} loading={create.isPending || update.isPending}>
            {editing ? 'Guardar' : 'Crear credencial'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

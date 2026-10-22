import {
  Alert,
  Button,
  Card,
  Group,
  PasswordInput,
  PinInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertCircle } from '@tabler/icons-react';
import { useState, type ReactNode } from 'react';
import { errorMessage } from '@/api/errors';
import type { AccountCode } from '@/api/types';
import { PageHeader } from '@/components/PageHeader';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  useChangeEmail,
  useChangePassword,
  useCurrentUser,
  useRequestEmailCode,
  useRequestPasswordCode,
  useUpdateProfile,
} from './api';

const MIN_LENGTH = 10;

function ErrorAlert({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
      {errorMessage(error)}
    </Alert>
  );
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <Title order={4} mb={4}>
        {title}
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        {description}
      </Text>
      {children}
    </Card>
  );
}

/** Campo del codigo de 6 digitos que llego al email, con "mandar otro". */
function CodeField({
  sent,
  value,
  onChange,
  onResend,
  resending,
}: {
  sent: AccountCode;
  value: string;
  onChange: (v: string) => void;
  onResend: () => void;
  resending: boolean;
}) {
  return (
    <Stack gap={6}>
      <Text size="sm">
        Mandamos un código a <b>{sent.sent_to}</b>. Vale hasta el {formatDateTime(sent.expires_at)}.
      </Text>
      <PinInput
        length={6}
        type="number"
        oneTimeCode
        autoFocus
        value={value}
        onChange={onChange}
        aria-label="Código del email"
        getInputProps={(i) => ({ 'aria-label': `Dígito ${i + 1} del código` })}
      />
      <Group gap="xs">
        <Button variant="subtle" size="compact-sm" onClick={onResend} loading={resending}>
          Mandar otro código
        </Button>
      </Group>
    </Stack>
  );
}

function NameCard() {
  const me = useCurrentUser();
  const update = useUpdateProfile();
  const [name, setName] = useState(me.name);
  return (
    <SectionCard title="Tus datos" description="Tu nombre aparece en los mails que te mandamos.">
      <Stack>
        <TextInput
          label="Nombre"
          placeholder="Ana Pérez"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
        />
        <TextInput label="Email de ingreso" value={me.email} readOnly disabled />
        <Group justify="flex-end">
          <Button
            disabled={name.trim() === me.name}
            loading={update.isPending}
            onClick={() =>
              update.mutate(
                { name },
                {
                  onSuccess: (r) => {
                    setName(r.name);
                    notifySuccess('Nombre guardado.');
                  },
                  onError: (e) => notifyError(e, 'No se pudo guardar'),
                },
              )
            }
          >
            Guardar
          </Button>
        </Group>
      </Stack>
    </SectionCard>
  );
}

function EmailCard() {
  const me = useCurrentUser();
  const request = useRequestEmailCode();
  const change = useChangeEmail();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState<AccountCode | null>(null);
  const [code, setCode] = useState('');

  const ask = () =>
    request.mutate(email.trim(), {
      onSuccess: (r) => {
        setSent(r);
        setCode('');
        change.reset();
      },
    });
  const reset = () => {
    setSent(null);
    setCode('');
    setEmail('');
    request.reset();
    change.reset();
  };
  const confirm = () =>
    change.mutate(
      { challenge: sent!.challenge, code },
      {
        onSuccess: (r) => {
          reset();
          notifySuccess(`Email cambiado. Desde ahora ingresás con ${r.email}.`);
        },
      },
    );

  return (
    <SectionCard
      title="Email de ingreso"
      description={`Para cambiarlo te mandamos un código a tu email actual (${me.email}). Las otras sesiones abiertas se cierran.`}
    >
      {!sent ? (
        <Stack>
          <TextInput
            label="Email nuevo"
            type="email"
            placeholder="vos@empresa.com"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
          />
          <ErrorAlert error={request.error} />
          <Group justify="flex-end">
            <Button onClick={ask} disabled={!email.includes('@')} loading={request.isPending}>
              Mandar código
            </Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          <Text size="sm">
            Email nuevo: <b>{email.trim().toLowerCase()}</b>
          </Text>
          <CodeField
            sent={sent}
            value={code}
            onChange={setCode}
            onResend={ask}
            resending={request.isPending}
          />
          <ErrorAlert error={change.error ?? request.error} />
          <Group justify="flex-end">
            <Button variant="default" onClick={reset}>
              Cancelar
            </Button>
            <Button onClick={confirm} disabled={code.length !== 6} loading={change.isPending}>
              Cambiar email
            </Button>
          </Group>
        </Stack>
      )}
    </SectionCard>
  );
}

function PasswordCard() {
  const me = useCurrentUser();
  const request = useRequestPasswordCode();
  const change = useChangePassword();
  const [sent, setSent] = useState<AccountCode | null>(null);
  const form = useForm({
    initialValues: { code: '', password: '', confirm: '' },
    validate: {
      code: (v) => (v.length === 6 ? null : 'Ingresá los 6 dígitos del código'),
      password: (v) => (v.length >= MIN_LENGTH ? null : `Usá al menos ${MIN_LENGTH} caracteres`),
      confirm: (v, values) => (v === values.password ? null : 'Las claves no coinciden'),
    },
  });

  const ask = () =>
    request.mutate(undefined, {
      onSuccess: (r) => {
        setSent(r);
        form.setFieldValue('code', '');
        change.reset();
      },
    });
  const reset = () => {
    setSent(null);
    form.reset();
    request.reset();
    change.reset();
  };

  return (
    <SectionCard
      title="Clave"
      description="Para cambiarla te mandamos un código a tu email. Las otras sesiones abiertas se cierran."
    >
      {!sent ? (
        <Stack>
          <ErrorAlert error={request.error} />
          <Group justify="flex-end">
            <Button onClick={ask} loading={request.isPending}>
              Mandar código
            </Button>
          </Group>
        </Stack>
      ) : (
        <form
          noValidate
          onSubmit={form.onSubmit((v) =>
            change.mutate(
              { challenge: sent.challenge, code: v.code, password: v.password },
              {
                onSuccess: () => {
                  reset();
                  notifySuccess('Clave cambiada.');
                },
              },
            ),
          )}
        >
          {/* El navegador ofrece guardar la clave nueva contra este email. */}
          <input type="text" name="username" autoComplete="username" value={me.email} readOnly hidden />
          <Stack>
            <CodeField
              sent={sent}
              value={form.values.code}
              onChange={(v) => form.setFieldValue('code', v)}
              onResend={ask}
              resending={request.isPending}
            />
            {form.errors.code && (
              <Text size="xs" c="red">
                {form.errors.code}
              </Text>
            )}
            <PasswordInput
              label="Clave nueva"
              description={`Al menos ${MIN_LENGTH} caracteres.`}
              autoComplete="new-password"
              {...form.getInputProps('password')}
            />
            <PasswordInput
              label="Repetí la clave"
              autoComplete="new-password"
              {...form.getInputProps('confirm')}
            />
            <ErrorAlert error={change.error ?? request.error} />
            <Group justify="flex-end">
              <Button variant="default" onClick={reset}>
                Cancelar
              </Button>
              <Button type="submit" loading={change.isPending}>
                Cambiar clave
              </Button>
            </Group>
          </Stack>
        </form>
      )}
    </SectionCard>
  );
}

/** Perfil del usuario de la sesion (admin o cliente): nombre, email de ingreso y clave. El email y la clave se
 * cambian con un código que llega al email actual. */
export function ProfilePage() {
  const me = useCurrentUser();
  return (
    <>
      <PageHeader title="Mi perfil" description={me.email} />
      <Stack gap="md" maw={720}>
        <NameCard />
        <EmailCard />
        <PasswordCard />
      </Stack>
    </>
  );
}

import {
  Alert,
  Box,
  Button,
  Card,
  Center,
  Image,
  Loader,
  PasswordInput,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useDocumentTitle } from '@mantine/hooks';
import { IconAlertCircle } from '@tabler/icons-react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { ApiError, errorMessage } from '@/api/errors';
import { usePasswordSetup, usePasswordSetupInfo } from './api';

const MIN_LENGTH = 10;

/** Crear la clave desde el link del mail de alta (/set-password?token=...). Al guardar queda con sesion. */
export function SetPasswordPage() {
  useDocumentTitle('Crear clave · Atentina');
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const info = usePasswordSetupInfo(token);
  const setup = usePasswordSetup();
  const navigate = useNavigate();

  const form = useForm({
    initialValues: { password: '', confirm: '' },
    validate: {
      password: (v) => (v.length >= MIN_LENGTH ? null : `Usá al menos ${MIN_LENGTH} caracteres`),
      confirm: (v, values) => (v === values.password ? null : 'Las claves no coinciden'),
    },
  });

  // Link vencido o ya usado (422), o sin token: lo que sigue es pedir otro, no reintentar.
  const linkError = !token
    ? 'Falta el link del mail. Abrilo de nuevo desde el email que te mandamos.'
    : info.error instanceof ApiError && info.error.status === 422
      ? info.error.message
      : info.isError
        ? errorMessage(info.error)
        : null;

  return (
    <Center mih="100vh" p="md">
      <Box w="100%" maw={400}>
        <Stack align="center" mb="lg">
          <Image src="/atentina-logo.svg" alt="Atentina" h={40} w="auto" />
          <Text c="dimmed" size="sm">
            Agentes de voz telefónicos
          </Text>
        </Stack>
        <Card>
          {linkError ? (
            <Stack>
              <Title order={2}>Este link ya no sirve</Title>
              <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
                {linkError}
              </Alert>
              <Button component={Link} to="/login" variant="default" fullWidth>
                Ir a ingresar
              </Button>
            </Stack>
          ) : !info.data ? (
            <Center py="md">
              <Loader aria-label="Verificando el link" />
            </Center>
          ) : (
            <>
              <Title order={2} mb={4}>
                Creá tu clave
              </Title>
              <Text c="dimmed" size="sm" mb="md">
                {info.data.client_name ? `${info.data.client_name} · ` : ''}
                {info.data.email}
              </Text>
              <form
                onSubmit={form.onSubmit((values) =>
                  setup.mutate(
                    { token, password: values.password },
                    { onSuccess: () => void navigate('/', { replace: true }) },
                  ),
                )}
                noValidate
              >
                {/* El navegador ofrece guardar la clave contra este email. */}
                <input
                  type="text"
                  name="username"
                  autoComplete="username"
                  value={info.data.email}
                  readOnly
                  hidden
                />
                <Stack>
                  <PasswordInput
                    label="Clave nueva"
                    description={`Al menos ${MIN_LENGTH} caracteres.`}
                    autoComplete="new-password"
                    autoFocus
                    {...form.getInputProps('password')}
                  />
                  <PasswordInput
                    label="Repetí la clave"
                    autoComplete="new-password"
                    {...form.getInputProps('confirm')}
                  />
                  {setup.isError && (
                    <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
                      {errorMessage(setup.error)}
                    </Alert>
                  )}
                  <Button type="submit" loading={setup.isPending} fullWidth>
                    Guardar y entrar
                  </Button>
                </Stack>
              </form>
            </>
          )}
        </Card>
      </Box>
    </Center>
  );
}

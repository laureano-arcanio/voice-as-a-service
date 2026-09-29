import {
  Alert,
  Box,
  Button,
  Center,
  Image,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertCircle } from '@tabler/icons-react';
import { Navigate, useLocation, useNavigate, type Location } from 'react-router';
import { ApiError, errorMessage } from '@/api/errors';
import { useComputedColorScheme } from '@mantine/core';
import { useDocumentTitle } from '@mantine/hooks';
import { useLogin, useMe } from './api';

function loginError(err: unknown): string {
  if (err instanceof ApiError && err.status === 429) {
    return 'Demasiados intentos. Esperá unos minutos y probá de nuevo.';
  }
  if (err instanceof ApiError && err.status === 401) return 'Email o clave incorrectos.';
  return errorMessage(err);
}

export function LoginPage() {
  const me = useMe();
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const scheme = useComputedColorScheme('light');
  useDocumentTitle('Ingresar · Oíme');
  const from = (location.state as { from?: Location } | null)?.from;
  const target = from && from.pathname !== '/login' ? `${from.pathname}${from.search}` : '/';

  const form = useForm({
    initialValues: { email: '', password: '' },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v.trim()) ? null : 'Ingresá un email válido'),
      password: (v) => (v ? null : 'Ingresá tu clave'),
    },
  });

  if (me.data) return <Navigate to={target} replace />;

  return (
    <Center mih="100vh" p="md" style={{ background: 'var(--oime-page-bg)' }}>
      <Box w="100%" maw={400}>
        <Stack align="center" mb="lg">
          <Image
            src={scheme === 'dark' ? '/oime-logo-blanco.svg' : '/oime-logo.svg'}
            alt="Oíme"
            h={48}
            w="auto"
          />
          <Text c="dimmed" size="sm">
            Agentes de voz telefónicos
          </Text>
        </Stack>
        <Paper p="xl" radius="md" shadow="sm">
          <form
            onSubmit={form.onSubmit((values) =>
              login.mutate(
                { email: values.email.trim(), password: values.password },
                { onSuccess: () => void navigate(target, { replace: true }) },
              ),
            )}
            noValidate
          >
            <Stack>
              <TextInput
                label="Email"
                type="email"
                autoComplete="username"
                placeholder="vos@empresa.com"
                autoFocus
                {...form.getInputProps('email')}
              />
              <PasswordInput
                label="Clave"
                autoComplete="current-password"
                {...form.getInputProps('password')}
              />
              {login.isError && (
                <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
                  {loginError(login.error)}
                </Alert>
              )}
              <Button type="submit" loading={login.isPending} fullWidth>
                Ingresar
              </Button>
            </Stack>
          </form>
        </Paper>
        <Text ta="center" size="xs" c="dimmed" mt="md">
          ¿Te olvidaste la clave? Pedile una nueva a tu administrador.
        </Text>
      </Box>
    </Center>
  );
}

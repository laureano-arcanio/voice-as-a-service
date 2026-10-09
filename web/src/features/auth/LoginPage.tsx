import {
  Alert,
  Box,
  Button,
  Card,
  Center,
  Image,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertCircle } from '@tabler/icons-react';
import { Navigate, useLocation, useNavigate, useSearchParams, type Location } from 'react-router';
import { ApiError, errorMessage } from '@/api/errors';
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
  useDocumentTitle('Ingresar · Atentina');
  // Los mails traen /login?email=...: el campo viene lleno y el foco va a la clave.
  const [params] = useSearchParams();
  const prefilled = params.get('email')?.trim() ?? '';
  const from = (location.state as { from?: Location } | null)?.from;
  const target = from && from.pathname !== '/login' ? `${from.pathname}${from.search}` : '/';

  const form = useForm({
    initialValues: { email: prefilled, password: '' },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v.trim()) ? null : 'Ingresá un email válido'),
      password: (v) => (v ? null : 'Ingresá tu clave'),
    },
  });

  if (me.data) return <Navigate to={target} replace />;

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
          <Title order={2} mb="md">
            Ingresá a tu cuenta
          </Title>
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
                autoFocus={!prefilled}
                {...form.getInputProps('email')}
              />
              <PasswordInput
                label="Clave"
                autoComplete="current-password"
                autoFocus={!!prefilled}
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
        </Card>
        <Text ta="center" size="xs" c="dimmed" mt="md">
          ¿Te olvidaste la clave? Pedile una nueva a tu administrador.
        </Text>
      </Box>
    </Center>
  );
}

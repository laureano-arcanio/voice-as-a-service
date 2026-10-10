import { Alert, Box, Button, Card, Center, Image, Loader, Stack, Text, Title } from '@mantine/core';
import { useDocumentTitle } from '@mantine/hooks';
import { IconAlertCircle } from '@tabler/icons-react';
import { useEffect, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { errorMessage } from '@/api/errors';
import { useHandoff } from './api';

/** Ruta interna segura (sin otro host). */
function safeNext(next: string | null): string {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/';
}

/** Llegada desde el registro de la landing (/welcome?token=...&next=...): abre la sesion con el link de un
 * solo uso y sigue a `next`. El pago con tarjeta (/plan/pagar) se abre con navegacion completa por su CSP. */
export function WelcomePage() {
  useDocumentTitle('Bienvenido · Atentina');
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const next = safeNext(params.get('next'));
  const handoff = useHandoff();
  const navigate = useNavigate();
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    handoff.mutate(token, {
      onSuccess: () => {
        if (next.startsWith('/plan/pagar')) window.location.replace(next);
        else void navigate(next, { replace: true });
      },
    });
  }, [token, next, handoff, navigate]);

  const failed = !token || handoff.isError;
  return (
    <Center mih="100vh" p="md">
      <Box w="100%" maw={400}>
        <Stack align="center" mb="lg">
          <Image src="/atentina-logo.svg" alt="Atentina" h={40} w="auto" />
        </Stack>
        <Card>
          {failed ? (
            <Stack>
              <Title order={2}>Ingresá a tu cuenta</Title>
              <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
                {token ? errorMessage(handoff.error) : 'Falta el link del registro.'}
              </Alert>
              <Button component={Link} to="/login" fullWidth>
                Ir a ingresar
              </Button>
            </Stack>
          ) : (
            <Stack align="center" py="md">
              <Loader aria-label="Abriendo tu cuenta" />
              <Text size="sm" c="dimmed">
                Abriendo tu cuenta…
              </Text>
            </Stack>
          )}
        </Card>
      </Box>
    </Center>
  );
}

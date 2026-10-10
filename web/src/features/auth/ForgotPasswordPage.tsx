import { Alert, Box, Button, Card, Center, Image, Stack, Text, TextInput, Title } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useDocumentTitle } from '@mantine/hooks';
import { IconAlertCircle, IconMailCheck } from '@tabler/icons-react';
import { Link, useSearchParams } from 'react-router';
import { ApiError, errorMessage } from '@/api/errors';
import { usePasswordReset } from './api';

/** "Olvidé mi clave": manda el link para crear una nueva. La respuesta es la misma exista o no el email. */
export function ForgotPasswordPage() {
  useDocumentTitle('Recuperar la clave · Atentina');
  const [params] = useSearchParams();
  const reset = usePasswordReset();
  const form = useForm({
    initialValues: { email: params.get('email')?.trim() ?? '' },
    validate: { email: (v) => (/^\S+@\S+\.\S+$/.test(v.trim()) ? null : 'Ingresá un email válido') },
  });

  return (
    <Center mih="100vh" p="md">
      <Box w="100%" maw={400}>
        <Stack align="center" mb="lg">
          <Image src="/atentina-logo.svg" alt="Atentina" h={40} w="auto" />
        </Stack>
        <Card>
          {reset.isSuccess ? (
            <Stack>
              <Title order={2}>Revisá tu email</Title>
              <Alert color="green" icon={<IconMailCheck size={18} />}>
                Si {reset.variables} tiene una cuenta, te mandamos un link para crear una clave nueva. Si no
                llega en unos minutos, mirá en spam.
              </Alert>
              <Button component={Link} to="/login" variant="default" fullWidth>
                Volver a ingresar
              </Button>
            </Stack>
          ) : (
            <>
              <Title order={2} mb={4}>
                Recuperá tu clave
              </Title>
              <Text c="dimmed" size="sm" mb="md">
                Te mandamos un link para crear una clave nueva.
              </Text>
              <form onSubmit={form.onSubmit((v) => reset.mutate(v.email.trim()))} noValidate>
                <Stack>
                  <TextInput
                    label="Email"
                    type="email"
                    autoComplete="username"
                    placeholder="vos@empresa.com"
                    autoFocus
                    {...form.getInputProps('email')}
                  />
                  {reset.isError && (
                    <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert">
                      {reset.error instanceof ApiError && reset.error.status === 429
                        ? 'Pediste muchos links. Esperá un rato y probá de nuevo.'
                        : errorMessage(reset.error)}
                    </Alert>
                  )}
                  <Button type="submit" loading={reset.isPending} fullWidth>
                    Mandar el link
                  </Button>
                  <Button component={Link} to="/login" variant="subtle" fullWidth>
                    Volver a ingresar
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

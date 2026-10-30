import {
  ActionIcon,
  Anchor,
  Box,
  Button,
  Container,
  Group,
  Image,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { IconArrowLeft, IconArrowRight, IconCheck, IconPlayerPlayFilled, IconPlayerStopFilled } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { BrandLogo } from '@/branding/BrandLogo';
import { useLogout, useMe, useWelcomeSeen } from '@/features/auth/api';
import { LegalModal } from '@/features/auth/LegalModal';
import { voiceName } from '@/features/voices/names';
import { usePageTitle } from '@/branding/context';
import { QueryState } from '@/components/QueryState';
import { notifyError } from '@/lib/notify';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import { useCreateFirstAgent } from './api';
import { FEATURED_VOICES, INDUSTRY_UI, sampleOpening } from './catalog';
import { useSample } from './useSample';

function useIndustries() {
  return useQuery({
    queryKey: ['onboarding', 'industries'],
    queryFn: () => unwrap(api.GET('/api/v1/onboarding/industries')),
    staleTime: Infinity,
  });
}

/**
 * Asistente de primera vez (docs/features/PRIMERA_VEZ.md): pantalla completa, sin el menú, mientras el cliente
 * no tiene agentes. Rubro (y sitio), voz, y el agente sale de la plantilla del rubro. Al crearlo, el panel
 * pasa a Inicio con el agente listo para hablarle.
 */
export function OnboardingWizard() {
  usePageTitle('Creá tu agente');
  const { data: me } = useMe();
  const navigate = useNavigate();
  const logout = useLogout();
  const industries = useIndustries();
  const create = useCreateFirstAgent();
  const sample = useSample();
  const welcome = useWelcomeSeen();
  const [step, setStep] = useState<0 | 1>(0);
  const [industry, setIndustry] = useState<string | null>(null);
  const [website, setWebsite] = useState('');
  const [voice, setVoice] = useState<string>('sofia');
  const company = me?.client_name || 'tu empresa';
  const top = useRef<HTMLDivElement>(null);

  // El asistente reemplaza la bienvenida: no aparece después, en el panel.
  const welcomed = useRef(false);
  useEffect(() => {
    if (me?.welcome_pending && !welcomed.current) {
      welcomed.current = true;
      welcome.mutate();
    }
  }, [me?.welcome_pending, welcome]);

  const go = (s: 0 | 1) => {
    sample.stop();
    setStep(s);
    top.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const submit = () => {
    if (!industry) return;
    sample.stop();
    create.mutate(
      { industry, voice, website: website.trim() },
      {
        onSuccess: (agent) => {
          // Después de navegar: Inicio carga diferido y, si el panel aparece antes en "/", su redirección a
          // /inicio pisa esta (sin ?nuevo).
          void Promise.resolve(navigate(`/inicio?nuevo=${agent.id}`, { replace: true })).then(create.done);
        },
        onError: (e) => notifyError(e, 'No se pudo crear el agente'),
      },
    );
  };

  return (
    <Box className="onb-page" ref={top}>
      <LegalModal />
      <Group className="onb-top" justify="space-between" wrap="nowrap">
        <BrandLogo h={28} />
        <Anchor
          component="button"
          size="sm"
          c="dimmed"
          onClick={() => logout.mutate(undefined, { onSuccess: () => void navigate('/login', { replace: true }) })}
        >
          Salir
        </Anchor>
      </Group>
      <Container size={880} py="xl" px="md">
        <Stack gap="xl">
          <Stack gap={6} align="center" ta="center">
            <Text className="label" c="blue">
              Paso {step + 1} de 2
            </Text>
            <Title order={1} className="onb-title">
              {step === 0 ? `Armemos el agente de ${company}` : 'Elegí la voz de tu agente'}
            </Title>
            <Text c="dimmed" maw={560}>
              {step === 0
                ? 'Contanos a qué se dedica tu negocio y te dejamos un agente listo para hablarle. Después lo ajustás a tu medida.'
                : `Así va a saludar a quien se comunique con ${company}. Dale play para escucharla.`}
            </Text>
          </Stack>

          {step === 0 ? (
            <QueryState query={industries}>
              {(list) => (
                <Stack gap="lg">
                  <SimpleGrid cols={{ base: 1, xs: 2, sm: 3 }} spacing="sm">
                    {list.map((item) => {
                      const ui = INDUSTRY_UI[item.id] ?? INDUSTRY_UI.otro;
                      const selected = industry === item.id;
                      return (
                        <UnstyledButton
                          key={item.id}
                          className="onb-option"
                          data-selected={selected || undefined}
                          aria-pressed={selected}
                          onClick={() => setIndustry(item.id)}
                        >
                          <Group justify="space-between" align="flex-start" wrap="nowrap" mb="xs">
                            <ThemeIcon size={44} radius="xl" variant={selected ? 'filled' : 'light'}>
                              <ui.icon size={24} stroke={1.6} />
                            </ThemeIcon>
                            {selected && <IconCheck size={20} color="var(--mantine-color-blue-6)" />}
                          </Group>
                          <Text fw={600}>{item.label}</Text>
                          <Text size="sm" c="dimmed">
                            {ui.detail}
                          </Text>
                        </UnstyledButton>
                      );
                    })}
                  </SimpleGrid>
                  <TextInput
                    label="Sitio web de tu negocio (opcional)"
                    placeholder="tuempresa.com.ar"
                    maw={420}
                    value={website}
                    onChange={(e) => setWebsite(e.currentTarget.value)}
                  />
                  <Group justify="flex-end">
                    <Button size="md" rightSection={<IconArrowRight size={18} />} disabled={!industry} onClick={() => go(1)}>
                      Elegir la voz
                    </Button>
                  </Group>
                </Stack>
              )}
            </QueryState>
          ) : (
            <Stack gap="lg">
              <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
                {FEATURED_VOICES.map((v) => {
                  const selected = voice === v.id;
                  const name = voiceName(v.id);
                  const busy = sample.loading === v.id;
                  const sounding = sample.playing === v.id;
                  return (
                    <Box
                      key={v.id}
                      className="onb-option onb-voice"
                      data-selected={selected || undefined}
                      role="button"
                      tabIndex={0}
                      aria-pressed={selected}
                      onClick={() => setVoice(v.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setVoice(v.id);
                        }
                      }}
                    >
                      <Box className="onb-portrait" data-sounding={sounding || undefined}>
                        <Image src={`/voces/${v.id}.svg`} alt={`Retrato de ${name}`} className="onb-portrait-img" />
                      </Box>
                      <Group gap={6} justify="center">
                        <Text fw={700} size="lg">
                          {name}
                        </Text>
                        {selected && <IconCheck size={18} color="var(--mantine-color-blue-6)" />}
                      </Group>
                      <Text size="sm" c="dimmed" ta="center">
                        {v.tagline}
                      </Text>
                      <Tooltip label={sounding ? 'Parar' : `Escuchar a ${name}`} withArrow>
                        <ActionIcon
                          size="lg"
                          radius="xl"
                          variant={sounding ? 'filled' : 'light'}
                          aria-label={sounding ? 'Parar' : `Escuchar a ${name}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setVoice(v.id);
                            if (sounding || busy) sample.stop();
                            else void sample.play(v.id, sampleOpening(name, company));
                          }}
                        >
                          {busy ? (
                            <Loader size={16} color="blue" />
                          ) : sounding ? (
                            <IconPlayerStopFilled size={16} />
                          ) : (
                            <IconPlayerPlayFilled size={16} />
                          )}
                        </ActionIcon>
                      </Tooltip>
                    </Box>
                  );
                })}
              </SimpleGrid>
              <Group justify="space-between">
                <Button variant="default" leftSection={<IconArrowLeft size={18} />} onClick={() => go(0)}>
                  Volver
                </Button>
                <Button size="md" rightSection={<IconArrowRight size={18} />} loading={create.isPending} onClick={submit}>
                  Crear mi agente con {voiceName(voice)}
                </Button>
              </Group>
            </Stack>
          )}
        </Stack>
      </Container>
    </Box>
  );
}

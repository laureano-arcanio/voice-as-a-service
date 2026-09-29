import {
  createTheme,
  defaultVariantColorsResolver,
  type VariantColorsResolver,
  virtualColor,
  type CSSVariablesResolver,
  type MantineColorsTuple,
} from '@mantine/core';

// Marca Oíme: navy #14213D, acento ambar #F4A63A (soft #FDF1DC), ok #1E9E6A.
const navy: MantineColorsTuple = [
  '#edf0f6',
  '#d5dbe8',
  '#a9b5cf',
  '#7b8db4',
  '#56699b',
  '#2f4270',
  '#14213D',
  '#111c34',
  '#0d162a',
  '#090f1e',
];

const amber: MantineColorsTuple = [
  '#fff8eb',
  '#FDF1DC',
  '#fbe0b3',
  '#f8cd84',
  '#F6B45A',
  '#F4A63A',
  '#e8962a',
  '#cc7f1c',
  '#a86614',
  '#86500d',
];

const green: MantineColorsTuple = [
  '#e7f7f0',
  '#d0eee1',
  '#a2dcc3',
  '#70c9a3',
  '#48b988',
  '#2faa77',
  '#1E9E6A',
  '#17865a',
  '#10774f',
  '#026641',
];

// Modo oscuro: fondo #0F1626 (dark-7), superficie #182238 (dark-6).
const dark: MantineColorsTuple = [
  '#D5DBE7',
  '#AEB7C9',
  '#8993A8',
  '#667189',
  '#3C4966',
  '#2A3650',
  '#182238',
  '#0F1626',
  '#0B111E',
  '#070B14',
];

// El primario es navy en claro y ambar en oscuro (color virtual): el texto encima
// tiene que cambiar con el esquema, cosa que autoContrast no puede calcular.
const variantColorResolver: VariantColorsResolver = (input) => {
  const r = defaultVariantColorsResolver(input);
  if (input.variant === 'filled' && (input.color ?? input.theme.primaryColor) === 'primary') {
    return { ...r, color: 'var(--oime-on-primary)' };
  }
  return r;
};

export const theme = createTheme({
  variantColorResolver,
  primaryColor: 'primary',
  primaryShade: { light: 6, dark: 4 },
  autoContrast: true,
  luminanceThreshold: 0.4,
  colors: {
    navy,
    amber,
    green,
    dark,
    primary: virtualColor({ name: 'primary', light: 'navy', dark: 'amber' }),
  },
  defaultRadius: 'md',
  fontFamily:
    'Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
  headings: { fontWeight: '650' },
  components: {
    Card: { defaultProps: { withBorder: true, padding: 'lg' } },
    Paper: { defaultProps: { withBorder: true } },
    Table: { defaultProps: { verticalSpacing: 'xs', highlightOnHover: true } },
    Badge: { defaultProps: { variant: 'light', radius: 'sm' } },
    Modal: { defaultProps: { centered: true } },
  },
});

export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  light: {
    '--mantine-color-default-border': '#DCE1EA',
    '--mantine-color-dimmed': '#5B6578',
    '--mantine-color-text': '#14213D',
    '--oime-page-bg': '#F4F6F9',
    '--oime-on-primary': '#FFFFFF',
    '--oime-accent': '#F4A63A',
    '--oime-accent-soft': '#FDF1DC',
  },
  dark: {
    '--mantine-color-default-border': '#2A3650',
    '--oime-page-bg': '#0F1626',
    '--oime-on-primary': '#14213D',
    '--oime-accent': '#F6B45A',
    '--oime-accent-soft': 'rgba(246, 180, 90, 0.14)',
  },
});

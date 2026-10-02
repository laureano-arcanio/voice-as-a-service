import {
  Badge,
  createTheme,
  defaultVariantColorsResolver,
  Modal,
  rem,
  Tabs,
  type CSSVariablesResolver,
  type MantineColorsTuple,
  type VariantColorsResolver,
} from '@mantine/core';

// Tema de la marca Atentina: docs/DESIGN_GUIDELINE_APP.md, seccion 11. Solo claro.
// Las escalas pisan los nombres de Mantine: color="green" o c="dimmed" ya dan el color de la marca.
const blue: MantineColorsTuple = [
  '#eaf0ff',
  '#dbe5ff',
  '#c7d5ff',
  '#b3c6ff',
  '#9db6ff',
  '#5681f6',
  '#2456e6',
  '#1740b8',
  '#12339a',
  '#0e287a',
];

const green: MantineColorsTuple = [
  '#e3f6ec',
  '#c9ecd9',
  '#a3dcbd',
  '#74c99b',
  '#45b47b',
  '#1b9c5b',
  '#147a46',
  '#10653a',
  '#0c502e',
  '#083b22',
];

const yellow: MantineColorsTuple = [
  '#fdf3e7',
  '#fae3c5',
  '#f6cd95',
  '#f0b360',
  '#e69a35',
  '#cc7a14',
  '#ad5008',
  '#92400e',
  '#78350f',
  '#5c2a0c',
];

const red: MantineColorsTuple = [
  '#fef3f2',
  '#fde0dc',
  '#f9c0b9',
  '#f39a90',
  '#ea6f62',
  '#d6402f',
  '#b42318',
  '#912018',
  '#7a1b14',
  '#5f1510',
];

const gray: MantineColorsTuple = [
  '#f6f8fb',
  '#f1f4f9',
  '#e9edf3',
  '#e3e8ef',
  '#cbd5e1',
  '#94a3b8',
  '#64748b',
  '#33415c',
  '#1c2740',
  '#0b1220',
];

const INK = '#0b1220';
const SHADOW_CARD = '0 12px 34px rgba(11, 18, 32, 0.08)';
const SHADOW_DIALOG = '0 24px 60px rgba(11, 18, 32, 0.25)';
const HEADINGS = "'Bricolage Grotesque Variable', 'Figtree Variable', system-ui, sans-serif";

// Pildora neutra de la marca: superficie gris y texto secundario. El gris al 10 % que arma
// Mantine no se distingue sobre una fila en hover y su texto no llega a 4,5:1.
const variantColorResolver: VariantColorsResolver = (input) => {
  const r = defaultVariantColorsResolver(input);
  if (input.variant === 'light' && input.color === 'gray') {
    return {
      ...r,
      background: 'var(--mantine-color-gray-2)',
      hover: 'var(--mantine-color-gray-3)',
      color: 'var(--mantine-color-gray-7)',
    };
  }
  return r;
};

export const theme = createTheme({
  variantColorResolver,
  colors: { blue, green, yellow, red, gray },
  primaryColor: 'blue',
  primaryShade: 6,
  black: INK,
  white: '#ffffff',
  fontFamily: "'Figtree Variable', system-ui, sans-serif",
  fontFamilyMonospace: "'IBM Plex Mono', ui-monospace, monospace",
  headings: {
    fontFamily: HEADINGS,
    fontWeight: '700',
    sizes: {
      h1: { fontSize: rem(32), lineHeight: '1.15' },
      h2: { fontSize: rem(24), lineHeight: '1.15' },
      h3: { fontSize: rem(19), lineHeight: '1.15' },
      h4: { fontSize: rem(17), lineHeight: '1.15' },
      h5: { fontSize: rem(15), lineHeight: '1.15' },
      h6: { fontSize: rem(14), lineHeight: '1.15' },
    },
  },
  radius: { xs: rem(6), sm: rem(8), md: rem(10), lg: rem(12), xl: rem(16) },
  defaultRadius: 'md',
  shadows: { xs: SHADOW_CARD, sm: SHADOW_CARD, md: SHADOW_CARD, lg: SHADOW_DIALOG, xl: SHADOW_DIALOG },
  components: {
    Card: { defaultProps: { withBorder: true, radius: 'xl', padding: 'lg' } },
    Paper: { defaultProps: { withBorder: true, radius: 'xl' } },
    Modal: Modal.extend({
      defaultProps: {
        centered: true,
        radius: 18,
        padding: 'lg',
        shadow: 'xl',
        overlayProps: { color: INK, backgroundOpacity: 0.45 },
      },
      styles: {
        // El contenido es un Paper: sin el borde que el tema les pone a las tarjetas.
        content: { border: 0 },
        title: { fontFamily: HEADINGS, fontWeight: 700, fontSize: rem(17), letterSpacing: '-0.015em' },
      },
    }),
    Badge: Badge.extend({
      defaultProps: { variant: 'light' },
      styles: { root: { textTransform: 'none', fontWeight: 600 } },
      // Mantine baja a 9-11 px en xs, sm y md: el piso de la app es 12 px.
      vars: (_theme, props) => ({
        root:
          props.size === 'lg' || props.size === 'xl'
            ? {}
            : { '--badge-fz': rem(12), '--badge-height': rem(22), '--badge-padding-x': rem(9) },
      }),
    }),
    Table: { defaultProps: { verticalSpacing: 'xs', highlightOnHover: true } },
    Tabs: Tabs.extend({
      defaultProps: { variant: 'pills' },
      // Seleccionado: acento suave y texto azul, no el relleno de Mantine.
      vars: () => ({
        root: {
          '--tabs-color': 'var(--mantine-color-blue-light)',
          '--tabs-text-color': 'var(--mantine-color-blue-light-color)',
        },
      }),
    }),
    Menu: { defaultProps: { shadow: 'md' } },
    Popover: { defaultProps: { shadow: 'md' } },
    Combobox: { defaultProps: { shadow: 'md' } },
    Notification: { defaultProps: { withBorder: true } },
    InputWrapper: { styles: { label: { fontWeight: 600 } } },
    Button: { styles: { root: { fontWeight: 600 } } },
    // Grilla y textos de los graficos: variables en styles.css.
    BarChart: { defaultProps: { maxBarWidth: 28 } },
    LineChart: { defaultProps: { strokeWidth: 2 } },
  },
});

export const cssVariablesResolver: CSSVariablesResolver = (t) => ({
  variables: {
    '--app-canvas': t.colors.gray[0],
    '--app-surface-2': t.colors.gray[1],
    '--app-line': t.colors.gray[3],
    // Series de los graficos, en este orden. Paleta validada para daltonismo.
    '--chart-1': '#2456e6',
    '--chart-2': '#b45309',
    '--chart-3': '#0d9488',
  },
  light: {},
  dark: {},
});

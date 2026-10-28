import { createTheme, type CSSVariablesResolver, type MantineThemeOverride } from '@mantine/core';
import type { Branding } from '@/api/types';
import { cssVariablesResolver, theme } from '@/theme';
import { INK, scale, WHITE } from './color';

/** El tema de Atentina con la marca del cliente encima (docs/ARQUITECTURA.md): la escala del primario
 * pisa a `blue`, así `color="blue"` y `--mantine-color-blue-*` siguen andando sin tocar ningún componente. */
export function brandTheme(branding: Branding | null): MantineThemeOverride {
  if (!branding) return theme;
  return createTheme({ ...theme, colors: { ...theme.colors, blue: scale(branding.color_primary) } });
}

/** Las variables de la app: las de siempre más el encabezado y las series de los gráficos de la marca. */
export function brandCssVariables(branding: Branding | null): CSSVariablesResolver {
  return (t) => {
    const base = cssVariablesResolver(t);
    return {
      ...base,
      variables: {
        ...base.variables,
        '--app-header-bg': branding?.color_header ?? WHITE,
        '--app-header-fg': branding?.header_fg ?? INK,
        // Línea del header: la del tema sobre fondo blanco; sobre un color, el texto al 20 %.
        '--app-header-line':
          !branding || branding.color_header === WHITE
            ? t.colors.gray[3]
            : `color-mix(in srgb, ${branding.header_fg} 20%, transparent)`,
        '--chart-1': branding?.color_primary ?? base.variables['--chart-1'],
        '--chart-2': branding?.color_accent ?? base.variables['--chart-2'],
      },
    };
  };
}

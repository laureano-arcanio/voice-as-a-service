import '@fontsource-variable/figtree';
import '@fontsource-variable/bricolage-grotesque';
import '@fontsource/ibm-plex-mono/latin-400.css';
import '@fontsource/ibm-plex-mono/latin-500.css';
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/charts/styles.css';
import '@mantine/notifications/styles.css';
import './styles.css';
import 'dayjs/locale/es';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { PREVIEW_KEY } from './branding/context';
import { bootPanelSession } from './features/auth/switch';
import { adoptSupportFromUrl } from './features/support/session';

// Pestaña abierta con "ver como cliente" (antes del primer pedido a la API).
adoptSupportFromUrl(PREVIEW_KEY);

// Llega desde el teléfono con un pase de sesión (#sesion=): se abre antes de pedir `me`.
void bootPanelSession().finally(() =>
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  ),
);

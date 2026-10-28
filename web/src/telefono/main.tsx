import '@fontsource-variable/figtree';
import '@fontsource-variable/bricolage-grotesque';
import '@fontsource/ibm-plex-mono/latin-400.css';
import '@fontsource/ibm-plex-mono/latin-500.css';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import '../styles.css';
import './telefono.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { bootPhoneSession } from '@/features/auth/switch';
import { PhoneRoot } from './PhoneRoot';

// La sesión del panel: con el pase (#sesion=) o, sin sesión, probando una vez con la del panel.
void bootPhoneSession()
  .catch(() => true)
  .then((stay) => {
    if (!stay) return;
    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <PhoneRoot />
      </StrictMode>,
    );
  });

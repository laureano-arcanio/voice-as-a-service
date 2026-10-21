import { createHashRouter } from 'react-router';
import { NotFound, RouteError } from '@/components/NotFound';
import { CrmLayout } from './Layout';
import { CampaignPage } from './pages/CampaignPage';
import { CampaignsPage } from './pages/CampaignsPage';
import { LeadPage } from './pages/LeadPage';
import { LeadsPage } from './pages/LeadsPage';
import { MessagesPage } from './pages/MessagesPage';
import { StatsPage } from './pages/StatsPage';
import { TemplatesPage } from './pages/TemplatesPage';
import { TodayPage } from './pages/TodayPage';

// Hash: la misma URL anda en el servicio (/) y en desarrollo (/crm.html), sin reglas de fallback.
export const crmRouter = createHashRouter([
  {
    element: <CrmLayout />,
    errorElement: <RouteError />,
    children: [
      { path: '/', element: <TodayPage /> },
      { path: '/leads', element: <LeadsPage /> },
      { path: '/leads/:id', element: <LeadPage /> },
      { path: '/campanas', element: <CampaignsPage /> },
      { path: '/campanas/:id', element: <CampaignPage /> },
      { path: '/plantillas', element: <TemplatesPage /> },
      { path: '/mensajes', element: <MessagesPage /> },
      { path: '/tablero', element: <StatsPage /> },
      { path: '*', element: <NotFound /> },
    ],
  },
]);

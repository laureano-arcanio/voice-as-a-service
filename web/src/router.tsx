import type { ComponentType } from 'react';
import { createBrowserRouter, type RouteObject } from 'react-router';
import type { Role } from '@/api/types';
import { AppLayout } from '@/components/AppLayout';
import { NotFound, RouteError } from '@/components/NotFound';
import { FullPageLoader, RequireAuth, RequireRole } from '@/features/auth/guards';
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { SetPasswordPage } from '@/features/auth/SetPasswordPage';
import { WelcomePage } from '@/features/auth/WelcomePage';

/** Pagina cargada a demanda (code splitting por ruta), opcionalmente solo para un rol. */
function page(load: () => Promise<ComponentType>, role?: Role): Pick<RouteObject, 'lazy'> {
  return {
    lazy: async () => {
      const Page = await load();
      return {
        Component: role
          ? () => (
              <RequireRole role={role}>
                <Page />
              </RequireRole>
            )
          : Page,
      };
    },
  };
}

export const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage />, errorElement: <RouteError /> },
  { path: '/set-password', element: <SetPasswordPage />, errorElement: <RouteError /> },
  { path: '/forgot-password', element: <ForgotPasswordPage />, errorElement: <RouteError /> },
  { path: '/welcome', element: <WelcomePage />, errorElement: <RouteError /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    errorElement: <RouteError />,
    hydrateFallbackElement: <FullPageLoader />,
    children: [
      {
        index: true,
        ...page(async () => (await import('@/features/dashboard/DashboardPage')).DashboardPage),
      },
      {
        path: 'calls',
        ...page(async () => (await import('@/features/calls/ConversationsPage')).ConversationsPage),
      },
      {
        path: 'calls/:id',
        ...page(async () => (await import('@/features/calls/CallDetailPage')).CallDetailPage),
      },
      { path: 'agents', ...page(async () => (await import('@/features/agents/AgentsPage')).AgentsPage) },
      {
        path: 'agents/:id',
        ...page(async () => (await import('@/features/agents/AgentDetailPage')).AgentDetailPage),
      },
      { path: 'voices', ...page(async () => (await import('@/features/voices/VoicesPage')).VoicesPage) },
      {
        path: 'developers',
        ...page(async () => (await import('@/features/developers/DevelopersPage')).DevelopersPage, 'client'),
      },
      {
        path: 'usage',
        ...page(async () => (await import('@/features/clients/UsagePage')).UsagePage, 'client'),
      },
      {
        path: 'account',
        ...page(async () => (await import('@/features/clients/AccountPage')).AccountPage, 'client'),
      },
      { path: 'plan', ...page(async () => (await import('@/features/billing/PlanPage')).PlanPage, 'client') },
      {
        path: 'plan/pagar',
        ...page(async () => (await import('@/features/billing/CheckoutPage')).CheckoutPage, 'client'),
      },
      {
        path: 'clients',
        ...page(async () => (await import('@/features/clients/ClientsPage')).ClientsPage, 'admin'),
      },
      {
        path: 'clients/:id',
        ...page(async () => (await import('@/features/clients/ClientDetailPage')).ClientDetailPage, 'admin'),
      },
      {
        path: 'numbers',
        ...page(async () => (await import('@/features/numbers/NumbersPage')).NumbersPage, 'admin'),
      },
      {
        path: 'campaigns',
        ...page(async () => (await import('@/features/campaigns/CampaignsPage')).CampaignsPage),
      },
      {
        path: 'campaigns/:id',
        ...page(async () => (await import('@/features/campaigns/CampaignDetailPage')).CampaignDetailPage),
      },
      {
        path: 'whatsapp',
        ...page(async () => (await import('@/features/whatsapp/WhatsAppPage')).WhatsAppPage),
      },
      { path: 'tiers', ...page(async () => (await import('@/features/tiers/TiersPage')).TiersPage, 'admin') },
      {
        path: 'billing',
        ...page(async () => (await import('@/features/billing/BillingPage')).BillingPage, 'admin'),
      },
      { path: 'users', ...page(async () => (await import('@/features/users/UsersPage')).UsersPage, 'admin') },
      { path: '*', element: <NotFound /> },
    ],
  },
];

export const router = createBrowserRouter(routes);

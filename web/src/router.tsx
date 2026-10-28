import type { ComponentType } from 'react';
import { createBrowserRouter, Navigate, type RouteObject } from 'react-router';
import { AppLayout } from '@/components/AppLayout';
import { NotFound, RouteError } from '@/components/NotFound';
import { FullPageLoader, RequireAdminArea, RequireAuth, RequireClientArea } from '@/features/auth/guards';
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { SetPasswordPage } from '@/features/auth/SetPasswordPage';
import { WelcomePage } from '@/features/auth/WelcomePage';
import { OAuthConsentPage } from '@/features/oauth/OAuthConsentPage';

/** Pagina cargada a demanda (code splitting por ruta). */
function page(load: () => Promise<ComponentType>): Pick<RouteObject, 'lazy'> {
  return { lazy: async () => ({ Component: await load() }) };
}

export const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage />, errorElement: <RouteError /> },
  { path: '/set-password', element: <SetPasswordPage />, errorElement: <RouteError /> },
  { path: '/forgot-password', element: <ForgotPasswordPage />, errorElement: <RouteError /> },
  { path: '/welcome', element: <WelcomePage />, errorElement: <RouteError /> },
  // Consentimiento OAuth del servidor MCP: fuera del layout, con sesión (el login vuelve acá).
  {
    path: '/oauth/consent',
    element: (
      <RequireAuth>
        <OAuthConsentPage />
      </RequireAuth>
    ),
    errorElement: <RouteError />,
  },
  // Administración (docs/ARQUITECTURA.md): la plataforma y las vistas de todos los clientes.
  {
    path: '/admin',
    element: (
      <RequireAuth>
        <RequireAdminArea>
          <AppLayout />
        </RequireAdminArea>
      </RequireAuth>
    ),
    errorElement: <RouteError />,
    hydrateFallbackElement: <FullPageLoader />,
    children: [
      { index: true, element: <Navigate to="reports" replace /> },
      {
        path: 'reports',
        ...page(async () => (await import('@/features/reports/ReportsPage')).ReportsPage),
      },
      {
        path: 'calls',
        ...page(async () => (await import('@/features/calls/ConversationsPage')).ConversationsPage),
      },
      {
        path: 'calls/:id',
        ...page(async () => (await import('@/features/calls/CallDetailPage')).CallDetailPage),
      },
      {
        path: 'agents',
        ...page(async () => (await import('@/features/agents/AdminAgentsPage')).AdminAgentsPage),
      },
      {
        path: 'inference-requests',
        ...page(async () => (await import('@/features/api-requests/ApiRequestsPage')).ApiRequestsPage),
      },
      {
        path: 'clients',
        ...page(async () => (await import('@/features/clients/ClientsPage')).ClientsPage),
      },
      {
        path: 'clients/:id',
        ...page(async () => (await import('@/features/clients/ClientDetailPage')).ClientDetailPage),
      },
      {
        path: 'numbers',
        ...page(async () => (await import('@/features/numbers/NumbersPage')).NumbersPage),
      },
      { path: 'tiers', ...page(async () => (await import('@/features/tiers/TiersPage')).TiersPage) },
      {
        path: 'billing',
        ...page(async () => (await import('@/features/billing/BillingPage')).BillingPage),
      },
      {
        path: 'system',
        ...page(async () => (await import('@/features/system/SystemPage')).SystemPage),
      },
      { path: 'users', ...page(async () => (await import('@/features/users/UsersPage')).UsersPage) },
      { path: 'profile', ...page(async () => (await import('@/features/auth/ProfilePage')).ProfilePage) },
      { path: '*', element: <NotFound /> },
    ],
  },
  {
    path: '/',
    element: (
      <RequireAuth>
        <RequireClientArea>
          <AppLayout />
        </RequireClientArea>
      </RequireAuth>
    ),
    errorElement: <RouteError />,
    hydrateFallbackElement: <FullPageLoader />,
    children: [
      { index: true, element: <Navigate to="reports" replace /> },
      {
        path: 'reports',
        ...page(async () => (await import('@/features/reports/ReportsPage')).ReportsPage),
      },
      {
        path: 'calls',
        ...page(async () => (await import('@/features/calls/ConversationsPage')).ConversationsPage),
      },
      {
        path: 'calls/:id',
        ...page(async () => (await import('@/features/calls/CallDetailPage')).CallDetailPage),
      },
      {
        path: 'outbound',
        ...page(async () => (await import('@/features/outbound/OutboundCallsPage')).OutboundCallsPage),
      },
      { path: 'agents', ...page(async () => (await import('@/features/agents/AgentsPage')).AgentsPage) },
      {
        path: 'probar',
        ...page(async () => (await import('@/features/agents/TestAgentsPage')).TestAgentsPage),
      },
      {
        path: 'agents/:id',
        ...page(async () => (await import('@/features/agents/AgentDetailPage')).AgentDetailPage),
      },
      { path: 'voices', ...page(async () => (await import('@/features/voices/VoicesPage')).VoicesPage) },
      {
        path: 'models',
        ...page(async () => (await import('@/features/llm/ModelsPage')).ModelsPage),
      },
      { path: 'tools', ...page(async () => (await import('@/features/tools/ToolsPage')).ToolsPage) },
      { path: 'secrets', ...page(async () => (await import('@/features/tools/SecretsPage')).SecretsPage) },
      {
        path: 'tools/new',
        ...page(async () => (await import('@/features/tools/ToolEditorPage')).ToolEditorPage),
      },
      {
        path: 'tools/:slug',
        ...page(async () => (await import('@/features/tools/ToolEditorPage')).ToolEditorPage),
      },
      {
        path: 'developers',
        ...page(async () => (await import('@/features/developers/DevelopersPage')).DevelopersPage),
      },
      {
        path: 'inference-requests',
        ...page(async () => (await import('@/features/api-requests/ApiRequestsPage')).ApiRequestsPage),
      },
      {
        path: 'account',
        ...page(async () => (await import('@/features/clients/AccountPage')).AccountPage),
      },
      { path: 'profile', ...page(async () => (await import('@/features/auth/ProfilePage')).ProfilePage) },
      { path: 'plan', ...page(async () => (await import('@/features/billing/PlanPage')).PlanPage) },
      {
        path: 'plan/pagar',
        ...page(async () => (await import('@/features/billing/CheckoutPage')).CheckoutPage),
      },
      {
        path: 'contacts',
        ...page(async () => (await import('@/features/contacts/ContactsPage')).ContactsPage),
      },
      {
        path: 'contacts/:id',
        ...page(async () => (await import('@/features/contacts/ContactDetailPage')).ContactDetailPage),
      },
      { path: 'team', ...page(async () => (await import('@/features/team/TeamPage')).TeamPage) },
      {
        path: 'telefono',
        ...page(async () => (await import('@/features/phone/TelefonoPage')).TelefonoPage),
      },
      {
        path: 'telefono/llamada/:id',
        ...page(async () => (await import('@/features/phone/JoinCallPage')).JoinCallPage),
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
      { path: '*', element: <NotFound /> },
    ],
  },
];

export const router = createBrowserRouter(routes);

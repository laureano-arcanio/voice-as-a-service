import {
  IconBroadcast,
  IconKey,
  IconLockPassword,
  IconList,
  IconUser,
  IconAddressBook,
  IconApi,
  IconBuilding,
  IconCash,
  IconChartBar,
  IconChartHistogram,
  IconCode,
  IconCpu,
  IconCreditCard,
  IconFileInvoice,
  IconMessages,
  IconMicrophone,
  IconNotebook,
  IconPhone,
  IconPhoneCall,
  IconPhoneOutgoing,
  IconPlayerPlay,
  IconRobot,
  IconSpeakerphone,
  IconStack2,
  IconTool,
  IconUsers,
  IconUsersGroup,
  IconBrandWhatsapp,
} from '@tabler/icons-react';
import type { ComponentType } from 'react';
import type { PlanFeatureKey, Role } from '@/api/types';

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ size?: number; stroke?: number }>;
  /** La función del plan que necesita: sin ella, la navegación la marca con un candado. */
  feature?: PlanFeatureKey | PlanFeatureKey[];
}

/** Grupo desplegable del menú: se abre con un click y arranca abierto si contiene la pantalla actual. */
export interface NavGroup {
  label: string;
  icon: ComponentType<{ size?: number; stroke?: number }>;
  items: NavItem[];
}

export type NavEntry = NavItem | NavGroup;

export const isGroup = (e: NavEntry): e is NavGroup => 'items' in e;

// Menú del panel del cliente (también el de un admin que entró como el cliente).
export const CLIENT_NAV: NavEntry[] = [
  { to: '/reports', label: 'Reportes', icon: IconChartHistogram },
  { to: '/calls', label: 'Conversaciones', icon: IconMessages },
  {
    label: 'Agentes',
    icon: IconRobot,
    items: [
      { to: '/agents', label: 'Mis agentes', icon: IconList },
      // Lo que un agente usa va junto a los agentes (como Vapi y ElevenLabs), no en un grupo aparte.
      { to: '/tools', label: 'Herramientas', icon: IconTool, feature: 'custom_tools' },
      { to: '/secrets', label: 'Secretos', icon: IconLockPassword, feature: 'custom_tools' },
      { to: '/models', label: 'Modelos', icon: IconCpu },
      { to: '/probar', label: 'Playground', icon: IconPlayerPlay },
      { to: '/voices', label: 'Voces', icon: IconMicrophone },
    ],
  },
  {
    label: 'Canales',
    icon: IconBroadcast,
    items: [
      { to: '/whatsapp', label: 'WhatsApp', icon: IconBrandWhatsapp, feature: 'whatsapp' },
      { to: '/outbound', label: 'Llamadas del agente', icon: IconPhoneOutgoing, feature: 'outbound_calls' },
      { to: '/telefono', label: 'Teléfono del equipo', icon: IconPhoneCall, feature: 'direct_calls' },
      {
        to: '/campaigns',
        label: 'Campañas',
        icon: IconSpeakerphone,
        feature: ['campaigns_voice', 'campaigns_whatsapp'],
      },
    ],
  },
  {
    label: 'Agenda',
    icon: IconNotebook,
    items: [
      { to: '/contacts', label: 'Contactos', icon: IconAddressBook, feature: 'contacts' },
      { to: '/team', label: 'Equipo', icon: IconUsersGroup, feature: 'team' },
    ],
  },
  {
    label: 'Developers',
    icon: IconCode,
    items: [
      { to: '/developers', label: 'API keys', icon: IconKey },
      { to: '/inference-requests', label: 'Uso de la API', icon: IconApi },
    ],
  },
  {
    label: 'Cuenta',
    icon: IconUser,
    items: [
      { to: '/account', label: 'Mi cuenta', icon: IconFileInvoice },
      { to: '/plan', label: 'Plan', icon: IconCreditCard },
      { to: '/usage', label: 'Consumos', icon: IconChartBar },
    ],
  },
];

// Administración (/admin, docs/ADMIN_SOPORTE_PLAN.md): la plataforma y las vistas de todos los clientes. El
// resto se ve entrando como el cliente (ficha del cliente o link de una fila).
export const ADMIN_NAV: NavEntry[] = [
  { to: '/admin/reports', label: 'Reportes', icon: IconChartHistogram },
  { to: '/admin/calls', label: 'Conversaciones', icon: IconMessages },
  { to: '/admin/agents', label: 'Agentes', icon: IconRobot },
  { to: '/admin/inference-requests', label: 'Uso de la API', icon: IconApi },
  { to: '/admin/clients', label: 'Clientes', icon: IconBuilding },
  { to: '/admin/numbers', label: 'Números', icon: IconPhone },
  { to: '/admin/tiers', label: 'Tiers', icon: IconStack2 },
  { to: '/admin/billing', label: 'Cobros', icon: IconCash },
  { to: '/admin/users', label: 'Usuarios', icon: IconUsers },
];

/** El menú del área: la del cliente o la administración. */
export function navFor(role: Role): NavEntry[] {
  return role === 'admin' ? ADMIN_NAV : CLIENT_NAV;
}

/** Las pantallas del área, sin grupos. */
export function navItemsFor(role: Role): NavItem[] {
  return navFor(role).flatMap((e) => (isGroup(e) ? e.items : [e]));
}

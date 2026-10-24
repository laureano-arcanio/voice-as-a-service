import {
  IconBroadcast,
  IconKey,
  IconList,
  IconSettings,
  IconSitemap,
  IconUser,
  IconAddressBook,
  IconApi,
  IconApps,
  IconBuilding,
  IconCash,
  IconChartBar,
  IconCode,
  IconCpu,
  IconCreditCard,
  IconFileInvoice,
  IconHome,
  IconMessages,
  IconMicrophone,
  IconPhone,
  IconPhoneOutgoing,
  IconPlayerPlay,
  IconRobot,
  IconSpeakerphone,
  IconStack2,
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
  roles: Role[];
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

const BOTH: Role[] = ['admin', 'client'];

// Orden del menú. Las pantallas solo de admin van sueltas al final, bajo el rótulo "Administración".
export const NAV: NavEntry[] = [
  { to: '/', label: 'Inicio', icon: IconHome, roles: BOTH },
  { to: '/calls', label: 'Conversaciones', icon: IconMessages, roles: BOTH },
  {
    label: 'Agentes',
    icon: IconRobot,
    items: [
      { to: '/agents', label: 'Mis agentes', icon: IconList, roles: BOTH },
      { to: '/probar', label: 'Probar agentes', icon: IconPlayerPlay, roles: BOTH },
      { to: '/voices', label: 'Voces', icon: IconMicrophone, roles: BOTH },
    ],
  },
  {
    label: 'Canales',
    icon: IconBroadcast,
    items: [
      { to: '/whatsapp', label: 'WhatsApp', icon: IconBrandWhatsapp, roles: BOTH, feature: 'whatsapp' },
      { to: '/outbound', label: 'Llamadas', icon: IconPhoneOutgoing, roles: BOTH, feature: 'outbound_calls' },
      {
        to: '/campaigns',
        label: 'Campañas',
        icon: IconSpeakerphone,
        roles: BOTH,
        feature: ['campaigns_voice', 'campaigns_whatsapp'],
      },
    ],
  },
  {
    label: 'Organización',
    icon: IconSitemap,
    items: [
      { to: '/contacts', label: 'Contactos', icon: IconAddressBook, roles: BOTH, feature: 'contacts' },
      { to: '/team', label: 'Equipo', icon: IconUsersGroup, roles: BOTH, feature: 'team' },
    ],
  },
  {
    label: 'Configuración',
    icon: IconSettings,
    items: [
      { to: '/models', label: 'Modelos', icon: IconCpu, roles: ['client'] },
      { to: '/apps', label: 'Apps', icon: IconApps, roles: BOTH },
    ],
  },
  {
    // Las API keys del admin se gestionan por cliente, en su ficha: acá solo ve el uso.
    label: 'Developers',
    icon: IconCode,
    items: [
      { to: '/developers', label: 'API keys', icon: IconKey, roles: ['client'] },
      { to: '/inference-requests', label: 'Uso de la API', icon: IconApi, roles: BOTH },
    ],
  },
  {
    label: 'Cuenta',
    icon: IconUser,
    items: [
      { to: '/account', label: 'Mi cuenta', icon: IconFileInvoice, roles: ['client'] },
      { to: '/plan', label: 'Plan', icon: IconCreditCard, roles: ['client'] },
      { to: '/usage', label: 'Consumos', icon: IconChartBar, roles: ['client'] },
    ],
  },
  { to: '/clients', label: 'Clientes', icon: IconBuilding, roles: ['admin'] },
  { to: '/numbers', label: 'Números', icon: IconPhone, roles: ['admin'] },
  { to: '/tiers', label: 'Tiers', icon: IconStack2, roles: ['admin'] },
  { to: '/billing', label: 'Cobros', icon: IconCash, roles: ['admin'] },
  { to: '/users', label: 'Usuarios', icon: IconUsers, roles: ['admin'] },
];

/** El menú del rol: sin las pantallas que no ve y sin los grupos que quedan vacíos. */
export function navFor(role: Role): NavEntry[] {
  return NAV.flatMap((e): NavEntry[] => {
    if (!isGroup(e)) return e.roles.includes(role) ? [e] : [];
    const items = e.items.filter((i) => i.roles.includes(role));
    return items.length ? [{ ...e, items }] : [];
  });
}

/** Las pantallas del rol, sin grupos. */
export function navItemsFor(role: Role): NavItem[] {
  return navFor(role).flatMap((e) => (isGroup(e) ? e.items : [e]));
}

export function isAdminOnly(item: NavEntry): boolean {
  return !isGroup(item) && item.roles.length === 1 && item.roles[0] === 'admin';
}

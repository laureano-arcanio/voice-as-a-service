import {
  IconBuilding,
  IconFileInvoice,
  IconHome,
  IconMicrophone,
  IconPhone,
  IconRobot,
  IconStack2,
  IconUsers,
  IconBrandWhatsapp,
} from '@tabler/icons-react';
import type { ComponentType } from 'react';
import type { Role } from '@/api/types';

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ size?: number; stroke?: number }>;
  roles: Role[];
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Inicio', icon: IconHome, roles: ['admin', 'client'] },
  { to: '/agents', label: 'Agentes', icon: IconRobot, roles: ['admin', 'client'] },
  { to: '/voices', label: 'Voces', icon: IconMicrophone, roles: ['admin', 'client'] },
  { to: '/account', label: 'Mi cuenta', icon: IconFileInvoice, roles: ['client'] },
  { to: '/clients', label: 'Clientes', icon: IconBuilding, roles: ['admin'] },
  { to: '/numbers', label: 'Números', icon: IconPhone, roles: ['admin'] },
  { to: '/whatsapp', label: 'WhatsApp', icon: IconBrandWhatsapp, roles: ['admin', 'client'] },
  { to: '/tiers', label: 'Tiers', icon: IconStack2, roles: ['admin'] },
  { to: '/users', label: 'Usuarios', icon: IconUsers, roles: ['admin'] },
];

export function navItemsFor(role: Role): NavItem[] {
  return NAV_ITEMS.filter((i) => i.roles.includes(role));
}

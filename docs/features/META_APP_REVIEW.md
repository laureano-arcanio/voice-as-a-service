# App Review de Meta (app Atentina)

Estado de la revisión de Meta para la app `Atentina` (ID 2192489028351511, portafolio 897731003277295): Tech
Provider y acceso avanzado a `whatsapp_business_messaging` y `whatsapp_business_management`. Con los dos aprobados,
un cliente puede conectar su número con la app de Atentina por Embedded Signup ([WHATSAPP.md](WHATSAPP.md)).

Fuentes oficiales: [App Review para WhatsApp](https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/app-review)
y [Tech Providers](https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/get-started-for-tech-providers).

## Estado

Revisado en developers.facebook.com y Business Settings el 16-nov-2026.

| Paso | Estado |
|---|---|
| Verificación del negocio | Verificada el 1-oct-2026 (como *Sole Proprietorship*, nombre legal del titular, nombre alternativo "Atentina") |
| Verificación de acceso (Tech Provider) | Verificado: "Tu negocio se verificó como proveedor de tecnología" |
| App Review (solicitud 2192520205015060, enviada el 14-nov-2026) | Aprobada: `whatsapp_business_messaging`, `whatsapp_business_management` y `public_profile` |
| Comprobación de uso de datos (acción 2236853667248380) | Completada el 14-nov-2026 |
| Publicación de la app | Publicada |

- `business_management` no se pidió.
- La app "Atentina prueba cliente" (1123207140406119) es de pruebas, en desarrollo y sin webhook. El checklist de
  onboarding del MCP de WhatsApp Business la toma como referencia y marca pendientes que no son de la app de
  producción.
- El MCP de WhatsApp Business todavía responde `NOT_AVAILABLE` a `partner_onboarding_status` y `partner_clients`:
  los clientes conectados como partner no se pueden listar desde ahí.

## Pendientes

- Prender Embedded Signup y hacer la primera alta real: ver los pendientes de [WHATSAPP.md](WHATSAPP.md).
- Suscribir `smb_message_echoes` en Webhooks → WhatsApp Business Account (coexistencia): los ecos de lo que el dueño
  manda desde su app llegan por ese campo.
- Meta pide renovar cada año la comprobación de uso de datos; el aviso llega a las notificaciones de desarrollador.

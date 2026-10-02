# Seguimiento comercial

Registro de cada contacto: qué se envió, cuándo, si hubo seguimiento y qué contestó. Es la fuente
de verdad de la etapa de exploración ([`plan-salida-al-mercado.md`](plan-salida-al-mercado.md),
sección 0). Los textos exactos de cada envío están en [`envios/`](envios/).

Actualizado: 2-oct-2026.

## Resumen

| Métrica | Valor | Objetivo (plan, sección 8) |
|---|---|---|
| Contactos enviados | 10 | ~150 |
| Con seguimiento enviado | 0 | — |
| Respuestas | 0 | — |
| Conversaciones registradas | 0 | 30 en 60 días, de 5 rubros o más |
| Propuestas | 0 | ~8 |
| Pilotos | 0 | 3 en 90 días |

## Contactos

Una fila por empresa. Fechas en formato `d-mes` del 2026. `—` es "todavía no".

| # | Empresa | Rubro, lugar | Tipo | Email | Web | 1.er envío | Seguimiento | Respuesta | Estado | Próxima acción |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Instituto Oulton | Diagnóstico por imágenes, Córdoba | cliente | info@oulton.com.ar | https://institutoulton.com.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 2 | Cooperativa de Electricidad Bariloche (CEB) | Cooperativa eléctrica, Río Negro | cliente | correspondencia@ceb.coop | https://www.ceb.coop | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 3 | AMUR (Asociación Mutual Ruralista) | Mutual de salud, Santa Fe | cliente | info@amur.com.ar | https://www.amur.com.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 4 | MIS – Mutual Integral de Servicios | Mutual de préstamos, Santo Tomé (Santa Fe) | cliente | contacto@mis.org.ar | https://www.mis.org.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 5 | ISEP | Colegio privado, Mendoza | cliente | informes@isep.edu.ar | https://isep.edu.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 6 | GestarCoop | Software para cooperativas, Córdoba | canal | info@migestarcoop.com | https://migestarcoop.com | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 7 | Alianza Cobros | Estudio de cobranzas, CABA | cliente | propuestas@alianzacobros.com.ar | https://alianzacobros.com.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 8 | Paktar Cobranzas & BPO | Contact center, San Miguel (Bs. As.) | canal | info@paktar.com.ar | https://www.paktar.com.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 9 | Yacoub | Inmobiliaria, La Plata | cliente | info@yacoub.com.ar | https://yacoub.com.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |
| 10 | Grupo Silva (Silva Mobility) | Concesionaria, Tucumán | cliente | contacto@gruposilva.com.ar | https://silvamobility.com.ar | 2-oct | — | — | enviado | Seguimiento el 8-oct |

### Cómo se llena

- **1.er envío / Seguimiento:** la fecha en que salió. Máximo un seguimiento por contacto; si
  tampoco contesta, pasa a `sin respuesta` a los 7 días.
- **Respuesta:** fecha y una línea con lo que dijo (`9-oct: piden llamada, escribe la gerente`).
  Un rebote va acá (`rebotó`) y el estado pasa a `descartado` o se busca otro email.
- **Estado:** uno de
  `enviado` → `seguimiento enviado` → `respondió` → `charla agendada` → `charla hecha` →
  `propuesta` → `piloto`; o `sin respuesta`, `no interesa`, `descartado`.
- **Próxima acción:** qué y cuándo. Si no hay nada que hacer, `—`.
- No se borra una fila: un contacto cerrado queda con su estado final.

## Envíos

| Fecha | Tanda | Cantidad | Desde | Textos |
|---|---|---|---|---|
| 2-oct | Primeros 10, uno o dos por rubro | 10 | laureano@atentina.com.ar | [`envios/2026-10-02-primeros-10.md`](envios/2026-10-02-primeros-10.md) |

Reservas con email publicado, sin enviar: Infotech (sistema de turnos HORAS,
info@infotech.com.ar) y Estratega Software (software para cooperativas, Rosario,
contactanos@estrategasoftware.com.ar).

## Conversaciones

Una entrada por charla (llamada, reunión o intercambio de mails con contenido), aunque no termine
en venta. Son los campos de la sección 0 del plan.

Todavía no hay ninguna. Formato:

```
### <fecha> · <empresa> · <persona, cargo>

- Problema: qué llamadas o mensajes hacen hoy a mano.
- Volumen: cuántos por mes.
- Costo actual: quién los hace y cuánto les cuesta.
- Quién decide:
- ¿Pagaría un piloto?:
- Caso de uso: (turnos, cobranza, reclamos, otro)
- Próximo paso:
```

## Casos de uso que aparecen

Se cuenta en cuántas conversaciones aparece cada caso. Con 3, se justifica construir para él.

| Caso de uso | Conversaciones | Empresas |
|---|---|---|
| — | 0 | — |

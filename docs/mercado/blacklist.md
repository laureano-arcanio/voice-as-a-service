# Blacklist de emails

> **Congelado el 21-oct-2026.** El registro vigente es el CRM (`http://127.0.0.1:8030`, `make crm-up`; API en [`../CRM_API.md`](../CRM_API.md)), cargado desde este archivo, los `envios/` y el historial de Resend. No editar: lo nuevo va al CRM.

Direcciones a las que **no se manda ningún mail más**: ni primer contacto, ni seguimiento, ni otra tanda. Antes de armar
cualquier envío, cada destinatario se busca acá (también en minúsculas). La empresa puede seguir por otra casilla publicada,
LinkedIn o teléfono; lo que se bloquea es la dirección, salvo en "No contactar".

Actualizado: 19-oct-2026. Fuente de los rebotes: export de Resend (`last_event = bounced`) del 19-oct,
`scratch/envios/emails-sent-1792417956390.csv`. Al sumar una dirección: una fila, y la línea en "Respuesta" de su contacto en
[`seguimiento.md`](seguimiento.md).

## Rebotes

| # | Empresa | Email | Rebotó (envío del) |
|---|---|---|---|
| 7 | Alianza Cobros | lboechi@alianzacobros.com.ar | 5-oct |
| 10 | Grupo Silva (Silva Mobility) | contacto@gruposilva.com.ar | 2-oct |
| 43 | Mutual de Empleados del Banco de la Provincia de Córdoba (AMEBPC) | administracion@mutualbpc.com.ar | 5-oct |
| 45 | Mutual de Empleados de la Policía de Córdoba (AMEPPC) | afiliaciones@amepcba.org | 5-oct |
| 49 | Asociación Mutual Conexo | info@mutualconexo.com | 5-oct |
| 62 | Mutual 9 de Julio (Mutual de Asociados de la Asociación Deportiva 9 de Julio) | info@mutual9dejulio.com.ar | 5-oct |
| 73 | Mutual Metropolitana | mutualmetropolitana@yahoo.com.ar | 5-oct |
| 78 | Mutual Soberanía | contacto@mutualsoberania.com.ar | 5-oct |
| 79 | Mutual de Asociados del Club Atlético Atenas | ca-atenas@hotmail.com | 5-oct |
| 105 | TecnoVoz (Tecno Voz Noroeste S.A.) | info@tecnovoz.com | 6-oct, 14-oct |
| 114 | Ithreex Global | dyvanoff@ithreexglobal.com | 7-oct |
| 126 | Making Sense | mlaguna@makingsense.com | 14-oct |
| 134 | Henka (Digital Henka) | hello@digitalhenka.com | 7-oct |
| 139 | Biwares | drivero@biwares.com | 8-oct |
| 174 | BIT S.A. | bit@bit.com.ar | 8-oct |
| 213 | Cloud Solutions LATAM | hola@cloudsolutionslatam.com | 15-oct |
| 214 | HabSar | contact@habsar.com | 15-oct |
| 226 | PositiveIT | info@positiveit.com.ar | 15-oct |
| 239 | DinoCloud | info@dinocloud.co | 15-oct |
| 290 | AgroGi (CampoGi) | info@agrogi.com.ar | 15-oct |
| 297 | POSIT | comercial@positsistema.com | 16-oct |
| 322 | Legio | privacidad@legio.ai | 16-oct |
| 324 | Facturarg | soporte@facturarg.com | 16-oct |
| 335 | Flota360 | soporte@flota360.com.ar | 16-oct |
| 338 | ProCurva | hola@procurva.com | 16-oct |
| 340 | Aumo | hola@aumo.com.ar | 16-oct |

## No contactar (la empresa pidió no seguir o no le interesa)

| # | Empresa | Email | Motivo |
|---|---|---|---|
| 99 | Integrando Salud | (todas) | 19-oct: van a continuar con su proveedor actual |
| 191 | Datawise | (todas) | 14-oct: ya tienen esta solución; no interesa |

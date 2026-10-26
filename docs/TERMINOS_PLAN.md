# Términos y condiciones: aceptación, registro y botones de baja

Plan del 25-oct-2026. Objetivo: que cada cliente acepte en forma expresa una versión identificable de las
condiciones y de la política de privacidad, poder probarlo años después, y cumplir con los botones de
arrepentimiento y de baja. De paso, condiciones reescritas para proteger a Atentina (IA, datos, caídas, terceros).

No es asesoramiento legal: los textos los tiene que revisar un abogado antes de darlos por cerrados.

## 1. Qué exige la ley (Argentina, vigente a oct-2026)

No hay una forma obligatoria de "registrar" la aceptación: lo que se exige es poder **probarla**, y la carga es
de quien la invoca (un clic es firma electrónica, no digital: Ley 25.506, arts. 5 y 7).

| Norma | Qué pide | Cómo lo cumplimos |
|---|---|---|
| CCyC 985 | Cláusulas claras; las que remiten a textos no entregados se tienen por no convenidas | Link a la versión exacta en la casilla, y en el mail |
| CCyC 1106–1108 | Soporte electrónico vale como escrito; informar el medio; **confirmar por vía electrónica y sin demora** la aceptación | Mail de confirmación con versión, fecha, hash y link |
| CCyC 1110–1111, Ley 24.240 art. 34 | 10 días corridos para arrepentirse, informado | Cláusula, botón y formulario |
| Res. SCI 270/2020 (GMC 37/19), arts. 2–5 | Datos del proveedor, términos que se puedan leer y guardar sin alteración, **resumen** de lo importante, **confirmación expresa** (el silencio no vale) | Resumen arriba del texto, versión inmutable por URL, casilla desmarcada |
| Disp. SSDCyLC 954/2025 (y Disp. DNDC 3/2026) | Botón de arrepentimiento y **botón de baja**, a la vista y sin registro previo; código de trámite en 24 h; atención ≥ 8 h en días hábiles | `/arrepentimiento` y `/baja` en el pie de la landing y del panel; código al instante por mail |
| Ley 24.240 art. 37, Res. 53/2003 | Cambios unilaterales sin aviso, o exoneraciones totales de responsabilidad, son abusivos frente a consumidores | Aviso de 30 días y baja sin costo; topes "en la medida que la ley lo permita" |
| Ley 25.326 arts. 5, 6 y 25 | Consentimiento expreso e informado; el que presta servicios de tratamiento solo usa los datos según instrucciones | Aceptación de la política; cláusula de encargado en las condiciones |

Nuestros clientes son empresas, pero el registro está abierto a cualquiera y la jurisprudencia suele tratar como
consumidor al comercio chico: se cumple como si lo fueran.

## 2. Diseño

- **Textos con versión** en `app/legal/texts/<doc>/<versión>.md` (`terminos`, `privacidad`; versión = fecha de
  publicación, `2026-10-25`). Una versión publicada **no se edita**: un cambio es un archivo nuevo. `app/legal`
  calcula el SHA-256 de cada una y sabe cuál es la vigente.
- **La landing usa los mismos archivos:** `make legal-sync` los copia a `landing/src/data/legal/` (Render solo ve
  `landing/`), con `legal.json` (versiones y hashes). Un test falla si la copia quedó vieja. `/terminos` y
  `/privacidad` muestran la vigente y `/terminos/<versión>` y `/privacidad/<versión>`, cada versión anterior.
- **`legal_acceptances`** (migración 0031), solo de alta: usuario, cliente, email y nombre de la empresa en ese
  momento, documento, versión, hash, el texto de la casilla, canal (`signup`, `panel`), IP real, user agent y
  fecha UTC. **Sin claves foráneas**: la prueba sobrevive a que se borre el cliente.
- **Registro (`/registro`):** casilla obligatoria y desmarcada con links a la versión; el formulario manda las
  versiones que mostró y la API rechaza (409 `terms_outdated`) si no son las vigentes. La aceptación se guarda en la
  misma transacción que la cuenta: sin aceptación no hay cuenta.
- **Panel:** `GET /auth/me` trae `legal_pending` (documentos vigentes que el usuario no aceptó). Un modal que no se
  cierra pide aceptarlos (`POST /auth/me/legal`): cubre a los invitados por un admin, a los clientes de antes de
  este plan y a cada versión nueva. Solo usuarios de cliente; las API keys no se frenan (la aceptación es de la
  cuenta y el aviso de cambios va por mail).
- **Mail de confirmación** (CCyC 1108): el de bienvenida del registro, y uno propio al aceptar en el panel, con
  documento, versión, fecha, huella y link permanente.
- **Botones** `/arrepentimiento` y `/baja` en la landing (pie, a la vista): formulario sin cuenta, con Turnstile.
  `POST /api/v1/demo/consumer-requests` guarda el pedido (`consumer_requests`), manda el código (`ARR-…`/`BAJ-…`) al
  email del que pide y avisa a `CONTACT_TO`. El admin lo resuelve (baja en la ficha del cliente, devolución si es
  arrepentimiento) y lo marca: `GET/PATCH /api/v1/consumer-requests`. Con cuenta, la baja también es inmediata en
  Plan.
- **Conservación:** las aceptaciones y los pedidos no los borra la purga de registros sin activar ni la baja del
  cliente; van en el backup diario con el resto de la base. Mínimo: 5 años después del fin de la relación (CCyC 2560).

## 3. Condiciones (versión 2026-10-25)

Reescritas de cero. Lo que cubren, además de lo que ya estaba:

- **Resumen** de las cláusulas importantes arriba (Res. 270, art. 4).
- **IA:** puede equivocarse (transcripción, respuestas, datos tomados); no es asesoramiento profesional; no sirve para
  emergencias; el cliente configura, prueba, supervisa y responde frente a quien atiende el agente.
- **Responsabilidad del cliente:** contenido de los agentes, consentimientos (Ley 25.326, No Llame 26.951, aviso de
  grabación, trato digno en cobranzas), sistemas propios conectados (agente externo, webhooks, apps, LLM propio,
  agentes por MCP), credenciales y API keys.
- **Disponibilidad:** sin SLA salvo acuerdo escrito, mantenimiento, dependencia de terceros (telefonía, Meta,
  Cloudflare, Mercado Pago, energía); remedio único y acotado: crédito proporcional por caídas de más de 24 h
  atribuibles a Atentina.
- **Seguridad e incidentes:** medidas razonables, sin promesa de infalibilidad; aviso sin demora indebida; Atentina
  como encargado del tratamiento de los datos de las conversaciones; no responde por accesos con credenciales del
  cliente ni por sus sistemas.
- **Límite de responsabilidad:** sin daños indirectos; tope en lo pagado en los últimos 6 meses; salvo dolo o lo que la
  ley no permita excluir a consumidores. **Indemnidad** del cliente por su contenido y su uso.
- Precios, renovación, mora y caída al Free, ajustes con 30 días de aviso, arrepentimiento y baja, suspensión,
  terminación y exportación de datos (30 días), números de teléfono y cuentas de WhatsApp, demo, propiedad
  intelectual, confidencialidad, cambios de las condiciones, comunicaciones, ley y jurisdicción (Córdoba, salvo el
  domicilio del consumidor: CCyC 1109).

La política de privacidad pasa a archivo con versión, con lo que ya tenía más: Mercado Pago entre los proveedores,
qué guardamos de la aceptación y de los pedidos de baja, seguridad e incidentes, y aviso de cambios.

## 4. Fases

1. **Textos y versiones:** `app/legal/`, condiciones y privacidad nuevas, `make legal-sync`, páginas de la landing
   por versión, test de sincronía.
2. **Aceptación:** migración 0031 (`legal_acceptances`, `consumer_requests`), registro con casilla, mail, `legal_pending`
   y modal en el panel.
3. **Botones:** páginas `/arrepentimiento` y `/baja`, endpoint público, mails, API del admin y links en el pie del
   panel y de la landing.
4. **Despliegue** (lo pide el usuario): probar la 0031 contra una copia del backup, `make migrate`,
   `make calls-active && make up-agent`, publicar la landing. Los clientes actuales aceptan al entrar al panel.

## 5. Pendientes que decide el usuario

- Cerrados el 26-oct-2026: domicilio (Gral. Bustos 776, Cofico, Córdoba: condiciones, privacidad y pie de la
  landing), horario de atención (lunes a viernes hábiles, de 9 a 13 y de 14 a 18: 8 h) y revisión de un abogado.
  Los precios publicados siguen siendo finales.
- Vista del admin para los pedidos de baja (hoy: mail + API).

## 6. Estado

25-oct-2026: fases 1 a 3 implementadas, **sin desplegar**. Tests: `tests/test_legal.py` (19),
`tests/test_migration_0031.py`, `web/src/features/auth/LegalModal.test.tsx`; la suite completa pasa (el fallo de
`test_migration_0005` por `users.welcomed_at` es anterior a este plan).

| Pieza | Dónde |
|---|---|
| Textos y versiones | `app/legal/` (`texts/terminos/2026-10-01.md` es la versión anterior, archivada tal cual estaba) |
| Copia a la landing | `make legal-sync` → `landing/src/data/legal/`; páginas `LegalDoc.astro`, `/terminos/[version]`, `/privacidad/[version]` |
| Aceptación | `app/services/legal.py`, `app/models/legal.py`, migración 0031; registro en `signup.create_account` |
| API | `POST /demo/signup` (`accept_terms`, `terms_version`, `privacy_version`), `GET /demo/legal`, `GET /auth/me` (`legal_pending`), `POST /auth/me/legal`, `POST /demo/consumer-requests`, `GET/PATCH /consumer-requests` (admin) |
| Panel | `web/src/features/auth/LegalModal.tsx`; links legales al pie del menú (`AppLayout.tsx`) |
| Landing | casilla en `/registro`; `/arrepentimiento` y `/baja` (`ConsumerRequest.astro`); links en el pie |

Desvíos del diseño:

- La casilla del panel guarda su propio texto más las versiones (`services/legal.panel_text`), y valida solo los
  documentos pendientes: si un usuario ya aceptó la política y sale otra versión de las condiciones, acepta solo esa.
- Una versión publicada no se edita: `tests/test_legal.py::PUBLISHED` tiene el hash de cada una y falla si cambia.

## 7. Cómo desplegar

1. **Antes de publicar**, cerrar los pendientes de la sección 5 (domicilio, horario, impuestos). Si cambia el texto
   de `2026-10-25`, todavía no se publicó: editarlo, `make legal-sync` y actualizar su hash en `PUBLISHED`.
2. `make migrate-test` (la 0031 contra una copia del backup).
3. **Primero la landing** (push a `main`, Render): manda los campos nuevos, que la API vieja ignora. Al revés, la API
   nueva rechaza los registros de la landing vieja (`terms_required`).
4. `make migrate` y `make calls-active && make up-agent` (recrea `app` y `agent`). Hasta este paso, los formularios
   de `/baja` y `/arrepentimiento` dan error: hacerlo enseguida después del 3.
5. Probar: un registro de punta a punta (filas en `legal_acceptances`, mail con versiones y huellas), un pedido en
   `/baja` (código en pantalla y por mail, aviso a `CONTACT_TO`) y entrar al panel con un cliente existente (modal).
6. Avisar por mail a los clientes actuales que hay condiciones nuevas (el panel se las pide al entrar).

Una versión nueva más adelante: archivo nuevo `app/legal/texts/<slug>/<AAAA-MM-DD>.md`, su hash en `PUBLISHED`,
`make legal-sync`, aviso por mail con 30 días (punto 17 de las condiciones) y desplegar landing y `app` el día que rige.

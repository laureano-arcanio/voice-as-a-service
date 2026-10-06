# Plan: Mercado Pago en el mismo agente

Diseño (6-oct-2026). **Estado: análisis, sin código.** Lo que ya existe y se reusa es el canal de
WhatsApp ([`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md)): webhook, descarga de medios, cuentas por cliente con
token cifrado y el alta guiada (Embedded Signup). Las estimaciones son sin desglose fino, con las
2 semanas de la fase 1 de WhatsApp como referencia.

Responde:

1. **Cómo verificar el comprobante** (captura de pago o transferencia) que manda el cliente final del
   cliente de Atentina.
2. **Cómo se conecta la cuenta de Mercado Pago** de cada cliente.
3. **Si conviene invertir el flujo:** que el agente cobre con un link y la confirmación llegue sola.

## 0. Qué se confirmó y qué no

Fuente: documentación de Mercado Pago Developers, leída el 6-oct-2026.

| Tema | Estado |
|---|---|
| OAuth del vendedor (authorization code): `auth.mercadopago.com/authorization`, `state`, PKCE opcional, el `code` vale 10 min | Confirmado |
| Access token de 180 días; renovar con refresh token pide el scope `offline_access` | Confirmado |
| Consultar y buscar pagos, y órdenes comerciales, por API (`api.mercadopago.com`) | Confirmado |
| Reporte "Todas las transacciones": incluye **ingresos de dinero**, solo aprobados; se pide por `POST /v1/account/bank_report`, ventana de hasta 60 días, aviso por webhook; el medio de pago figura como `bank_transfer` | Confirmado, pero es un archivo asíncrono, no una consulta |
| Que una **transferencia común por alias o CVU** (sin link ni QR de Mercado Pago) aparezca en la búsqueda de pagos | **Sin confirmar**: la página de referencia devolvió 404 y las búsquedas no lo dicen. Es el punto que decide el diseño: spike de la fase 0 |
| Qué scopes de un token OAuth alcanzan para leer pagos del vendedor | Sin confirmar (misma causa) |
| Límites de pedidos y costo de la API | Sin confirmar; no se conoce costo por consulta |

## 1. Decisiones

Propuestas, a confirmar antes de la fase 0.

| Decisión | Elección | Por qué |
|---|---|---|
| Qué prueba un pago | **Un registro en la cuenta de Mercado Pago del cliente**, nunca la imagen | Una captura se falsifica en un minuto. La imagen solo dice qué buscar |
| Cómo se lee la imagen | **OCR en CPU** y extracción de campos (monto, fecha, nº de operación, origen, destino). Alternativa: visión del LLM | El OCR no toca las GPUs (el LLM está en 0.90 de la GPU 0). Gemma 4 trae encoder de imagen, hoy apagado con `--limit-mm-per-prompt image:0`; prenderlo cambia la config del LLM y hay que medirla (CAP). Elegir con 20-30 comprobantes reales en la fase 0 |
| Conexión de la cuenta | **OAuth por cliente**, desde el dashboard; tokens cifrados con Fernet | Mismo patrón que la cuenta de WhatsApp (`WaAccount`, `app/whatsapp/crypto.py`). El cliente no pega credenciales |
| Alcance inicial | **Solo lectura** | Verificar no necesita escribir en su cuenta. Cobrar con link (fase 2) sí |
| Quién decide si está pago | **La app, no el LLM** | El LLM redacta la respuesta con el resultado; no lo calcula |
| Cobro con link | **Fase 2**, comparte OAuth y webhook con la 1 | Es el camino sin fraude: el `external_reference` del link es la conversación, y el pago llega por webhook sin captura |

## 2. Flujo de verificación

```text
cliente final (WhatsApp)  -> imagen -> /wa/webhook -> WhatsAppService._on_image   (hoy responde wa_unsupported_reply)
                                          |
        Graph get_media + download_media (tope de bytes, igual que el audio)
                                          |
        app/payments/extract.py: OCR -> {monto, fecha, nº operación, origen, destino}
                                          |
        app/payments/verify.py: consulta a Mercado Pago con el token del cliente (GET /v1/payments/{id}, o búsqueda)
                                          |
        resultado -> línea de texto del turno -> engine.process_turn -> respuesta del agente
```

Es el mismo patrón del audio: el audio se convierte en texto del turno (`VOICE_NOTE_TAG`); el
comprobante se convierte en una línea con el veredicto. **El motor no tiene herramientas**
(function calling): extrae campos del diálogo. Por eso el resultado entra como texto y el workflow
cierra con un `outcome` (`pagado`, `pago_no_verificado`).

**Reglas de la verificación**

| Veredicto | Condición | El agente dice |
|---|---|---|
| `verified` | Existe, aprobado, destino = cuenta conectada, fecha dentro de la ventana, monto igual (o ≥) al esperado | Confirma y cierra |
| `duplicate` | El nº de operación ya se usó (único por cliente) | Que ese comprobante ya se registró |
| `mismatch` | Monto o destino no coinciden | El dato que no coincide; deriva a una persona |
| `not_found` | No hay registro todavía | "Lo estoy verificando": reintenta unas veces en ~30 min y deriva. **Nunca afirma que es falso**: una transferencia puede tardar |
| `unreadable` | El OCR no sacó los campos | Pide otra captura o el nº de operación por texto |

**El punto débil, según el tipo de pago:**

- **Pago por Mercado Pago** (dinero en cuenta, link, QR, tarjeta): el nº de operación del comprobante es el id del pago y se consulta directo. Fuerte.
- **Transferencia bancaria a alias o CVU:** el comprobante del banco trae otro identificador, que puede no existir como pago en la API. Si la búsqueda no los lista, queda el cruce por **monto + ventana de tiempo + nombre del ordenante** contra el reporte "Todas las transacciones" (asíncrono, minutos u horas). Más débil: con montos repetidos hay ambigüedad.

**Contra el fraude:** nº de operación único por cliente; destino igual a la cuenta conectada; fecha reciente; tope de imágenes por conversación y por hora; el texto crudo del OCR **no** llega al LLM (una captura puede traer instrucciones): solo los campos extraídos y el veredicto.

**Monto esperado:** hoy los agentes no consultan sistemas del cliente. Sin monto esperado, `verified` significa "hay un pago aprobado de $X a esta cuenta" y lo contrasta una persona. Con monto (campo de la conversación o dato que la API de `calls` pase al crearla), la app lo compara.

## 3. Conexión de la cuenta

- **Aplicación de Atentina** en Mercado Pago Developers (la crea el usuario): `MP_APP_ID`, `MP_CLIENT_SECRET`, `MP_WEBHOOK_SECRET` y la URL de redirección en `app.atentina.com.ar`.
- **Alta:** el cliente toca "Conectar Mercado Pago" en el dashboard → `auth.mercadopago.com/authorization` con `state` (CSRF, atado a su sesión) y PKCE → vuelve a `/api/v1/integrations/mercadopago/callback` → la app cambia el `code` por tokens (el `code` vale 10 min) → guarda ambos cifrados.
- **Renovación:** cron o tarea al arrancar que renueva antes de los 180 días; sin `offline_access`, el cliente tiene que reconectar cada 6 meses. Un 401 marca la cuenta `disconnected` (como WhatsApp con el error 190) y el dashboard avisa.
- **Webhook** `/mp/webhook` con la firma `x-signature` de Mercado Pago, por el mismo túnel que `wa.atentina.com.ar`: hay que agregar la ruta `^/mp/webhook` (la crea el usuario, como las otras). Hace falta en la fase 2 y para avisos de reportes.

## 4. Cómo encaja en la app

**Tablas nuevas** (migración `0008`):

| Tabla | Qué guarda |
|---|---|
| `mp_accounts` | `client_id` (única), `mp_user_id`, tokens cifrados, vencimiento, estado (`connected`/`disconnected`) |
| `mp_receipts` | `conversation_id`, `client_id`, nº de operación, monto, fecha, veredicto y motivo, hash SHA-256 de la imagen. Único `(client_id, operation_id)` |
| `mp_payment_links` | Fase 2: `preference_id`, `external_reference` (= conversación), monto, estado |

**Archivos:** `app/payments/` con `oauth.py`, `client.py` (httpx, un cliente por cuenta), `extract.py`,
`verify.py`, `webhook.py` y `store.py`; router `integrations` en `app/api/routers/`; pantalla
"Integraciones" en la vista de cliente de `web/` (guía [`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md)).

**Lo que se reusa:** descarga de medios y tope de bytes de `app/whatsapp/graph.py`; dedupe, un turno
a la vez por contacto y tope de turnos de `WhatsAppService`; `crypto.py` (generalizarlo fuera de
`app/whatsapp/`, con la misma clave o una `MP_TOKEN_KEY`); el túnel.

**Lo que hay que cambiar en el motor:** `TurnMedia` suma el origen del turno ("comprobante") y
`CHANNEL_RULES` (`app/llm/prompt.py`) la regla: el veredicto lo da la app y el agente no lo discute.
La imagen sigue sin guardarse: se guarda el hash y los campos.

**Datos personales:** un comprobante trae nombre y CUIT/CUIL del ordenante. Se borra la imagen al
extraer, los logs no llevan tokens ni campos del comprobante, y el hash alcanza para el duplicado.

**Capacidad:** con OCR en CPU no cambia el reparto de GPU; el agente gasta ~0,12 cores por llamada y
un OCR cuesta del orden de 1 s de CPU por imagen (a medir). Con visión del LLM sí: registrar un `CAP-NNN`.

## 5. Fases

| Fase | Contenido | Esfuerzo |
|---|---|---|
| 0. Spike | Cuenta real de Mercado Pago (la de Atentina) y una aplicación de prueba: (a) ¿una transferencia por alias aparece en `payments/search` o solo en el reporte?; (b) scopes mínimos; (c) OCR contra visión del LLM con 20-30 comprobantes reales de bancos y billeteras | 2-3 días |
| 1. Verificar comprobantes | OAuth + pantalla, imagen por WhatsApp, extractor, verificación por nº de operación, tablas, veredictos, agente de prueba (cobranzas "ya pagué") | ~2 semanas |
| 2. Cobrar con link | `preference` con `external_reference`, el agente manda el link por WhatsApp, webhook de pago, outcome `pagado` sin captura | ~1 semana |
| 3. Transferencias por reporte | Solo si el spike dice que no hay otra vía: cruce contra "Todas las transacciones" y reintentos | ~1 semana |
| 4. Voz | La llamada no recibe imágenes: el agente avisa que manda el link por WhatsApp (plantilla saliente, con costo de Meta) | A definir |

## 6. Respuestas del usuario (6-oct-2026) y qué implican

- **Se ofrece a los clientes de Atentina** (negocios), para verificar lo que les mandan sus propios clientes.
- **El pago normal es por alias o CVU.** Es justo el caso sin confirmar de la sección 0: **la fase 1 no se puede prometer** hasta el spike. Si la API de pagos no lista esas transferencias, el camino es el reporte (fase 3, más débil y con demora).
- **Alcance:** solo sirve si el alias o CVU del negocio es de **Mercado Pago**. Con el alias de un banco u otra billetera (Ualá, Brubank, etc.) no hay cuenta que consultar; no se investigó si esos tienen API para pymes. Antes de ofrecerlo, preguntarle al cliente dónde cobra.
- **Todavía no hay cuenta de Mercado Pago.** El spike necesita una **cuenta real**: las cuentas de prueba no reciben transferencias y sus reportes salen vacíos.

### Spike (fase 0), paso a paso

1. Abrir una cuenta de Mercado Pago (gratis; la de Atentina o una personal) y anotar su alias.
2. En Mercado Pago Developers, crear una aplicación y copiar el **access token de producción** de esa misma cuenta (para el spike no hace falta OAuth). Va a `.env` como `MP_SPIKE_TOKEN`, nunca al repo.
3. Mandarle $100 desde (a) un banco, (b) otra billetera y (c) otra cuenta de Mercado Pago, por alias; y un pago por link de la misma cuenta, para tener el caso fuerte de comparación.
4. Con el token, en `scratch/`: `GET /v1/payments/search` ordenado por fecha, `GET /v1/payments/{id}` con el nº del comprobante de cada uno, y un `POST /v1/account/bank_report` del día.
5. Anotar por cada origen: ¿aparece en la búsqueda?, ¿con qué campos (monto, ordenante, fecha)?, ¿coincide el nº del comprobante con algún id consultable?, ¿cuánto tarda el reporte?
6. Con los 3-4 comprobantes reales (y los que consigamos de clientes), probar OCR contra visión del LLM.

Resultado esperado del spike: una tabla "origen del pago → cómo se verifica → qué tan fuerte es" que se vuelca a la sección 2 y decide si va la fase 1, la 3 o solo la 2.

### Resultados del spike (parcial, 6-oct-2026)

Script: `scratch/mp_spike/spike.py` (solo lectura, token en `.env` como `MP_SPIKE_TOKEN`; el **Access Token**, no la Public Key, que tiene 44 caracteres y da 401/403). Cuenta personal; 32 movimientos en 3 días.

| Hallazgo | Dato |
|---|---|
| La búsqueda de pagos (`GET /v1/payments/search`) **sí lista una transferencia bancaria entrante a la cuenta** | `operation_type=account_fund`, `payment_type_id=bank_transfer`, `payment_method_id=cvu`, `sub_type=INTER_PSP`. Trae monto, fechas, `status`, `bank_transfer_id`, `transaction_id`, `e2e_id` y `financial_institution` |
| **No trae el ordenante** | `bank_info.payer` y `bank_info.collector` vienen todos en `null` (nombre, CUIT, cuenta, alias). El cruce por nombre no se puede; queda monto + fecha + identificador |
| Entre cuentas de Mercado Pago | `operation_type=money_transfer`, `sub_type=INTRA_PSP`, con `e2e_id` y sin `bank_transfer_id` ni datos del ordenante en lo propio |
| `GET /v1/account/movements/search` | 404: no existe, se descarta |
| `GET /v1/account/settlement_report/list` | 200, vacío (sin reportes configurados) |

**Caso 1 probado, de un tercero: transferencia de otra cuenta de Mercado Pago** (comprobante de $100, 6-oct-2026 16:26 hora argentina, "N.º de operación de Mercado Pago" 181727634837):

| Verificación | Resultado |
|---|---|
| Aparece en `GET /v1/payments/search` | Sí, a los 0 min (la consulta se hizo ~1 h después; la demora real sigue sin medirse) |
| `GET /v1/payments/181727634837` | 200. **El nº de operación del comprobante es el `id` del pago**: consulta directa, sin buscar |
| Campos que coinciden con el comprobante | `transaction_amount` = 100, `status` = `approved`, `collector_id` = la cuenta conectada, `date_created` 15:26 con offset -04:00 (= 16:26 -03:00, comparar con zona horaria) |
| Ordenante | `payer.id` y `payer.email` vienen; **el nombre y el CUIT no** (`bank_info` en `null`). Sirve para cruzar si el cliente conoce el mail o el id del pagador, no por nombre |
| Veredicto | **Verificación fuerte** para pagos entre cuentas de Mercado Pago |

**Caso 2 probado: transferencia de un banco (Santander) al alias/CVU** (comprobante de $100, 6-oct-2026, "Número de comprobante" 83732549, sin hora):

| Verificación | Resultado |
|---|---|
| Aparece en la búsqueda | Sí: pago `181728106651`, `account_fund` / `bank_transfer` / `cvu`, `approved`, `date_created` 15:29:04 (-04:00 = 16:29 ART) |
| El nº del comprobante del banco (83732549) figura en algún campo | **No.** No aparece en ningún campo del pago |
| Campos con los que sí se puede cruzar | `transaction_amount` (100), fecha y hora de acreditación, y `forward_data.cvu` (el CVU destino, con los primeros dígitos enmascarados; coincide con el del comprobante, pero es el mismo para todos los pagos del negocio) |
| Otros identificadores | `bank_transfer_id` y `transaction_id` = `e2e_id` (22 caracteres, el id de la transferencia inmediata). Santander **no lo muestra** en su comprobante; otros bancos podrían (a probar) |
| Ordenante | `payer.id` es la propia cuenta receptora; sin nombre, CUIT, banco ni cuenta de origen (`bank_info` en `null`) |
| Veredicto | **Verificación débil**: monto + ventana de tiempo + destino. Con dos pagos iguales en la ventana no se sabe cuál es de quién |

**Qué lo vuelve usable pese a eso:**

- **Monto único por conversación.** Al pedir el pago, el agente fija un importe con centavos que no se repite entre cobros abiertos (ej. $15.000,37). Es el truco habitual de conciliación en Argentina: el monto pasa a ser el identificador.
- **Un pago de la API se asigna a una sola conversación** (`mp_receipts` único por `(client_id, payment_id)`): una captura reenviada o dos clientes con el mismo monto no acreditan el mismo pago dos veces.
- Si el comprobante trae hora, ventana de ±10 min; si solo trae fecha (Santander), ventana del día más el monto único.
- Si hay más de un candidato, `ambiguous`: deriva a una persona, no acredita.
- Se puede además pedir el `e2e_id` / "ID de transacción" a los bancos que lo muestran.

**Lo que falta:** (1) otro banco que muestre ID coelsa o de transacción, para ver si coincide con `e2e_id`; (2) desde **otra billetera** (Ualá, Naranja X, Brubank): qué `payment_type_id` y qué datos; (3) la demora entre la transferencia y su aparición en la API: aquí apareció dentro de los ~2 min que pasaron hasta consultarla, sin medir mejor (hacer una y consultar a los 10 s y a los 60 s).

## 7. A decidir

1. **¿De dónde sale el monto esperado?** Dato de la conversación, o la API de `calls` lo recibe al crear la llamada.
2. **¿Atentina cobra comisión** sobre los cobros con link (`marketplace_fee`)? Cambia lo que se pide en el alta y el análisis fiscal.
3. **OCR o visión del LLM**, según el spike.
4. **Primer caso para probar:** cobranzas (`landing_cobranzas`: "ya pagué") es el más directo; turnos con seña, el segundo.
5. **Qué decirle ya a los clientes** que quieran esto: hasta el spike, "verificación de comprobantes de Mercado Pago, en validación"; no prometer alias de otros bancos.

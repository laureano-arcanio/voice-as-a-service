# API de Registros

Para la plataforma: el pre-call identifica por teléfono, una herramienta visible guarda la elección y el post-call registra el cobro. Base: `https://<registros>/v1`.

## Claves

`Authorization: Bearer <clave>`, creada con `create-key` (se muestra una vez).

| Alcance | Puede | Dónde va |
|---|---|---|
| `read` | `identify` y `identify/select` | Pre-call y herramienta visible |
| `charge` | Lo anterior y `charges` | **Solo el post-call** |

**Usá la clave `read` en todo, salvo en el post-call.** Una herramienta visible con otro nombre y clave `charge` hacia `/v1/charges` le deja cobrar al modelo. Con clave `read` recibe 403.

| Error | Cuándo |
|---|---|
| 401 | Sin clave, inválida o revocada |
| 403 | Clave `read` en `charges` |
| 422 | JSON inválido o campo faltante |
| 503 | Sin base. La plataforma lo reintenta como falla de transporte |

Los errores no llevan datos personales.

## `POST /v1/identify`

```json
{"conversation_id": "7f3c1a52-0e4b-4a7e-9d10-3b2f8c6a1d90", "from": "+5493515551234"}
```

Siempre responde estos seis campos, y solo estos: `status`, `name`, `al_dia`, `candidates`, `record`, `operator_note`. Sin datos clínicos, DNI ni teléfono.

| `status` | Cuándo | Qué trae |
|---|---|---|
| `single` | Una ficha, o una ya elegida en esta conversación | `name`, `al_dia`, `record`, `operator_note` |
| `multiple` | De 2 a 5 fichas | `candidates`, `record`, `operator_note` |
| `too_many` | Más de 5 fichas: no se puede elegir | `record`, `operator_note` |
| `none` | Sin ficha | `record` y `operator_note`: `Sin ficha` |
| `no_number` | `from` vacío, oculto o de menos de 8 dígitos | `record` y `operator_note`: `Sin teléfono` |
| `test` | `conversation_id` que no es un UUID | Todo nulo. No guarda nada |

Una ficha, titular:
```json
{
  "status": "single",
  "name": "María Gómez",
  "al_dia": true,
  "candidates": null,
  "record": "Ficha: https://registros.atentina.com.ar/c/3fa9c1e07b...",
  "operator_note": "María Gómez, titular, al día"
}
```
Teléfono cargado como contacto: `name` es `Contacto de María Gómez` y `operator_note`, `Contacto de María Gómez, no está al día`.

Varias fichas:
```json
{
  "status": "multiple",
  "name": null,
  "al_dia": null,
  "candidates": "María G. (r_1b2c); Juan G. (r_3d4e)",
  "record": "Este teléfono está en 2 fichas: https://registros.atentina.com.ar/c/8d21...",
  "operator_note": "Teléfono en 2 fichas, sin elegir todavía"
}
```
Las refs valen para esa conversación y ese `from`, durante 24 h. Repetir el pedido en la misma conversación reutiliza refs y token. Las fichas de baja no aparecen.

## `POST /v1/identify/select`

```json
{"conversation_id": "7f3c1a52-0e4b-4a7e-9d10-3b2f8c6a1d90", "from": "+5493515551234", "ref": "r_3d4e"}
```
```json
{"status": "selected", "name": "Juan Gómez", "al_dia": false, "record": "Ficha: https://registros.atentina.com.ar/c/8d21...", "operator_note": "Juan Gómez, no está al día"}
```
- `selected`: la elección queda guardada, y el link de la conversación abre solo esa ficha.
- `invalid`: ref inventada, de otra conversación, de otro `from`, vencida o de una ficha dada de baja. Todo nulo, así un `assign` no pisa lo que ya había.
- `test`: `conversation_id` que no es un UUID. Todo nulo.

Se puede volver a elegir: vale la última.

## `POST /v1/charges`

Solo con clave `charge`. Mismo cuerpo que `identify`. El cobro se calcula al recibirlo, así que no depende de que el pre-call haya funcionado. El monto es el del tenant, siempre al titular. Por ahora es simulado: `charges.status` es `simulated`.

| Estado, por orden | `charged` | `operator_message` |
|---|---|---|
| `conversation_id` que no es un UUID | `false`, con `test: true` | `Prueba: no se cobró.` |
| Ya hay cobro en la conversación | `true` | El mismo del primero |
| `from` vacío o de menos de 8 dígitos | `false` | `Sin ficha para este teléfono: no se cobró.` |
| Ficha elegida, de baja | `false` | `La ficha elegida está de baja: no se cobró.` |
| Ficha elegida, o `from` en una sola ficha | `true` | `Cobro registrado al titular Juan Pérez.` |
| Lo mismo, y no está al día | `true` | `Cobro registrado al titular Juan Pérez, que no está al día.` |
| Lo mismo, con teléfono de contacto | `true` | `Cobro registrado al titular Juan Pérez, por teléfono cargado como contacto.` |
| Contacto, y no está al día | `true` | `Cobro registrado al titular Juan Pérez, que no está al día, por teléfono cargado como contacto.` |
| `from` en varias fichas, sin elegir | `false` | `Este teléfono está en 2 fichas y no se eligió ninguna: no se cobró.` |
| `from` desconocido | `false` | `Sin ficha para este teléfono: no se cobró.` |

- **Sin doble cobro:** `UNIQUE(tenant_id, conversation_id)`. Repetir el pedido, también a la vez, da el mismo resultado.
- **`charged: false` no guarda fila** y no se reintenta: es una respuesta, no una falla.
- **La elección de ficha cuenta aunque hayan pasado las 24 h de las refs:** una conversación larga no le cobra a otra ficha.
- **Contacto con una sola ficha:** se le cobra a esa ficha y el mensaje lo dice. Una cuidadora que llama por otro paciente cobra a la ficha donde está cargada. Sin anulación por ahora.
- **Probar del panel:** usa `conversation_id="prueba"` y no cobra. Con un id real tipeado, **cobra**: es un acto deliberado.

`operator_message` se usa por texto. En voz no se oye, pero el cobro queda en el panel.

## `GET /health`

`{"status":"ok"}`, o 503 sin base o sin secreto de sesión. Sin clave.

## Herramientas de la plataforma

Los secretos del cliente son `REGISTROS_READ_KEY` y `REGISTROS_CHARGE_KEY`.

**`buscar_ficha`, oculta, pre-call:**
```json
{
  "description": "Busca la ficha por el teléfono, antes de la conversación.",
  "http": {
    "method": "POST",
    "url": "https://registros.atentina.com.ar/v1/identify",
    "auth": {"type": "bearer", "secret": "REGISTROS_READ_KEY"},
    "timeout_ms": 1200,
    "body": {"type": "object", "properties": {
      "conversation_id": {"type": "string", "value": "{{call.id}}"},
      "from": {"type": "string", "value": "{{call.phone}}"}
    }}
  },
  "assign": [
    {"var": "situacion_cliente", "path": "status"},
    {"var": "nombre", "path": "name"},
    {"var": "candidatos", "path": "candidates"},
    {"var": "al_dia", "path": "al_dia", "hide": true},
    {"var": "ficha", "path": "record", "hide": true},
    {"var": "nota_operador", "path": "operator_note", "hide": true}
  ]
}
```

**`elegir_persona`, visible:**
```json
{
  "description": "Guarda la ficha que confirmó la persona.",
  "http": {
    "method": "POST",
    "url": "https://registros.atentina.com.ar/v1/identify/select",
    "auth": {"type": "bearer", "secret": "REGISTROS_READ_KEY"},
    "timeout_ms": 1200,
    "body": {"type": "object", "required": ["ref"], "properties": {
      "conversation_id": {"type": "string", "value": "{{call.id}}"},
      "from": {"type": "string", "value": "{{call.phone}}"},
      "ref": {"type": "string", "description": "La ref de la opción que confirmó la persona"}
    }}
  },
  "assign": [
    {"var": "nombre", "path": "name"},
    {"var": "al_dia", "path": "al_dia", "hide": true},
    {"var": "ficha", "path": "record", "hide": true},
    {"var": "nota_operador", "path": "operator_note", "hide": true}
  ]
}
```

**`registrar_cobro`, oculta, post-call, con la clave `charge`:**
```json
{
  "description": "Registra el cobro al terminar.",
  "http": {
    "method": "POST",
    "url": "https://registros.atentina.com.ar/v1/charges",
    "auth": {"type": "bearer", "secret": "REGISTROS_CHARGE_KEY"},
    "timeout_ms": 2500,
    "retries": 0,
    "body": {"type": "object", "properties": {
      "conversation_id": {"type": "string", "value": "{{call.id}}"},
      "from": {"type": "string", "value": "{{call.phone}}"}
    }}
  }
}
```

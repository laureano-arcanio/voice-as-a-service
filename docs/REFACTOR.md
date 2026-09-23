Quiero que implementes un MVP de un motor conversacional basado en objetivos definidos en YAML.

La idea principal es NO implementar un chatbot basado en un guion rígido ni una FSM tradicional.

En cambio:

* El workflow define qué información se desea obtener.
* Cada dato deseado es un objetivo conversacional.
* El estado de la conversación contiene los datos ya obtenidos.
* En cada turno se envían al LLM:

  * el workflow;
  * el estado actual;
  * el nuevo mensaje del usuario.
* El LLM debe:

  * extraer cualquier información nueva;
  * identificar qué objetivos siguen pendientes;
  * decidir cuál es el siguiente objetivo;
  * generar la respuesta al usuario.
* La aplicación actualiza el estado con el structured output del LLM.

Quiero una implementación simple, clara y fácil de extender.

No agregues arquitectura innecesaria.

## 1. Workflow YAML

Implementá soporte para workflows como este:

```yaml
id: sales_discovery
version: 1

agent:
  name: Sofia
  role: agente de ventas
  language: es-AR

objective:
  description: >
    Entender la empresa, su forma actual de controlar asistencia,
    su necesidad principal y determinar si desea coordinar una demo.

conversation:
  opening: "Hola, soy Sofia. ¿Con quién tengo el gusto de hablar?"

  rules:
    - Hablar de forma natural y breve.
    - Hacer normalmente una pregunta por vez.
    - No volver a preguntar información que ya fue obtenida.
    - Si una respuesta es ambigua o insuficiente, pedir aclaración.
    - Si el usuario hace una pregunta, responderla y luego continuar con el workflow.
    - No seguir rígidamente el orden si el usuario ya proporcionó información futura.
    - Nunca inventar información.
    - No presionar al usuario para coordinar una demo.

fields:

  contact_name:
    priority: 10
    description: Nombre de la persona
    required: true
    question: "¿Con quién tengo el gusto de hablar?"

  company_name:
    priority: 20
    description: Empresa donde trabaja
    required: true
    question: "¿En qué empresa trabajás?"

  company_activity:
    priority: 30
    description: Actividad principal de la empresa
    required: true
    question: "¿A qué se dedica la empresa?"

  employee_count:
    priority: 40
    description: Cantidad aproximada de empleados
    type: integer
    required: true
    question: "¿Cuántos empleados tienen, aproximadamente?"

  workforce_location:
    priority: 50
    description: >
      Dónde trabaja principalmente el personal:
      oficina, múltiples sucursales, calle o una combinación.
    required: true
    question: "¿Dónde trabaja el personal: en una oficina, en varias sucursales o en la calle?"

  attendance_process:
    priority: 60
    description: Cómo controlan actualmente asistencia y horarios
    required: true
    question: "¿Cómo controlan hoy la asistencia y los horarios del personal?"

  main_problem:
    priority: 70
    description: Principal problema o mejora que busca el cliente
    required: true
    question: "¿Qué es lo que más te gustaría resolver o mejorar hoy?"

  desired_timeline:
    priority: 80
    description: Cuándo le gustaría tener funcionando una solución
    required: true
    question: "¿Para cuándo te gustaría tenerlo funcionando?"

  decision_maker:
    priority: 90
    description: Quién participa o toma la decisión de compra
    required: true
    question: "¿Quién toma la decisión de sumar un sistema así en tu empresa?"

  wants_demo:
    priority: 100
    description: Si desea coordinar una demostración
    type: boolean
    required: true
    question: >
      ¿Te gustaría coordinar una demo sin compromiso con un asesor
      para verlo funcionando sobre tu operación?

  email:
    priority: 110
    description: Email para coordinar la demo
    type: email

    required_if:
      wants_demo: true

    question: "¿A qué correo te escribimos para coordinarla?"

completion:
  when: all_required_fields_completed

  message_if_demo:
    "Perfecto. Ya tengo la información necesaria para coordinar la demo."

  message_if_no_demo:
    "Perfecto. Gracias por contarme un poco más sobre la empresa."
```

## 2. Principio importante

`question` NO representa un paso obligatorio.

Es únicamente una pregunta sugerida que el modelo puede utilizar para obtener ese dato.

El verdadero objetivo es completar el campo.

Por ejemplo:

```yaml
main_problem:
  description: Principal problema o mejora que busca el cliente
  question: "¿Qué es lo que más te gustaría resolver o mejorar hoy?"
```

significa:

```text
objetivo = obtener main_problem
```

No significa:

```text
debo necesariamente decir exactamente esa pregunta
```

El LLM puede reformularla para que la conversación sea natural.

## 3. Conversation State

Implementá un estado sencillo:

```json
{
  "conversation_id": "uuid",
  "workflow_id": "sales_discovery",
  "status": "active",

  "fields": {
    "contact_name": null,
    "company_name": null,
    "company_activity": null,
    "employee_count": null,
    "workforce_location": null,
    "attendance_process": null,
    "main_problem": null,
    "desired_timeline": null,
    "decision_maker": null,
    "wants_demo": null,
    "email": null
  }
}
```

No quiero un `current_step` obligatorio.

El estado debe representar lo que sabemos, no en qué número de pregunta estamos.

Los campos no completados son simplemente objetivos pendientes.

## 4. Structured output del LLM

Cada turno debe devolver exactamente una estructura equivalente a:

```json
{
  "field_updates": {
    "company_activity": "Fabricación de autopartes",
    "employee_count": 80
  },

  "next_objective": "workforce_location",

  "assistant_message": "¿Dónde trabaja principalmente el personal: en la planta, en sucursales o en la calle?",

  "status": "active"
}
```

Definí un modelo tipado, por ejemplo con Pydantic.

Algo equivalente a:

```python
class AgentTurn(BaseModel):
    field_updates: dict[str, Any]
    next_objective: str | None
    assistant_message: str
    status: Literal["active", "completed"]
```

Si considerás necesario agregar un campo pequeño para robustez, hacelo, pero mantené el contrato minimalista.

No quiero chain-of-thought, reasoning ni explicaciones internas del modelo.

## 5. System prompt

Implementá un único system prompt reutilizable en todos los turnos.

Debe expresar aproximadamente estas reglas:

```text
Sos un agente conversacional que ejecuta un workflow.

En cada turno:

1. Leé la definición del workflow.
2. Leé el estado actual de la conversación.
3. Interpretá el nuevo mensaje del usuario.
4. Extraé toda la información relevante que haya proporcionado.
5. Podés actualizar múltiples campos en un mismo turno.
6. No actualices campos si la información es insuficiente o ambigua.
7. Determiná qué objetivos siguen pendientes.
8. Elegí el siguiente objetivo conversacional apropiado.
9. Generá una respuesta natural para continuar.

Reglas:

- No sigas las preguntas como un guion rígido.
- No vuelvas a preguntar información que ya conocés.
- El usuario puede proporcionar varios datos espontáneamente.
- Si una respuesta es ambigua, pedí aclaración.
- Si el usuario hace una pregunta, respondela y luego continuá naturalmente.
- Nunca inventes datos.
- Hacé normalmente una pregunta por turno.
- Respetá el idioma y reglas definidas en el workflow.
- Las respuestas deben ser breves, naturales y apropiadas para una conversación de voz.
- No menciones JSON, campos, workflow ni estados internos.
- Cuando todos los campos obligatorios estén completos, marcá la conversación como completed.
```

En cada request al LLM se debe incluir:

```text
WORKFLOW:
<workflow>

CURRENT STATE:
<state>

NEW USER MESSAGE:
<message>
```

## 6. Flujo del sistema

Quiero algo conceptualmente equivalente a:

```python
async def process_turn(
    workflow,
    state,
    user_message
) -> AgentTurn:

    result = await llm(...)

    validate_updates(result, workflow)

    for field, value in result.field_updates.items():
        state.fields[field] = value

    state.status = result.status

    save_state(state)

    return result
```

Separá claramente:

```text
WorkflowLoader
ConversationState
ConversationEngine
LLMClient
```

Pero no agregues más abstracciones de las necesarias.

## 7. Validación desde la aplicación

El LLM propone actualizaciones, pero la aplicación debe hacer validaciones básicas.

Por ejemplo:

* no permitir campos que no existen en el workflow;
* validar integer;
* validar boolean;
* validar email;
* aplicar `required_if`;
* comprobar realmente si se puede marcar `completed`.

El LLM NO debe ser la única autoridad para decidir que el workflow terminó.

Implementá:

```python
is_workflow_complete(workflow, state)
```

La aplicación debe recalcular el estado de finalización después de cada turno.

## 8. required_if

Soportá inicialmente solamente una condición sencilla como:

```yaml
required_if:
  wants_demo: true
```

Ejemplo:

* si `wants_demo = true`, `email` pasa a ser obligatorio;
* si `wants_demo = false`, no es necesario obtener email.

No construyas todavía un lenguaje complejo de expresiones.

## 9. Prioridades

`priority` define el orden sugerido de los objetivos.

Ejemplo:

```text
company_name = 20
company_activity = 30
employee_count = 40
```

Pero NO es una FSM.

Si el usuario dice:

```text
Soy Juan, trabajo en Acme, hacemos logística y somos 120 personas.
```

el sistema debe poder completar de una vez:

```json
{
  "contact_name": "Juan",
  "company_name": "Acme",
  "company_activity": "Logística",
  "employee_count": 120
}
```

y continuar directamente con el siguiente objetivo todavía pendiente.

## 10. Aclaraciones

Ejemplo:

Agente:

```text
¿Cuántos empleados tienen aproximadamente?
```

Usuario:

```text
Somos bastantes.
```

El modelo NO debe guardar:

```json
{
  "employee_count": "bastantes"
}
```

Debe devolver algo equivalente a:

```json
{
  "field_updates": {},
  "next_objective": "employee_count",
  "assistant_message": "¿Tenés una cantidad aproximada? Por ejemplo, menos de 20, entre 20 y 100, o más de 100.",
  "status": "active"
}
```

## 11. Preguntas del usuario

El workflow no debe impedir que exista una conversación normal.

Ejemplo:

Agente:

```text
¿Cómo controlan actualmente la asistencia?
```

Usuario:

```text
Usamos planillas. ¿El sistema permite fichar desde el celular?
```

Debe:

1. extraer:

```json
{
  "attendance_process": "Planillas"
}
```

2. responder la pregunta del usuario;
3. continuar con el siguiente objetivo.

Algo equivalente a:

```text
Sí, se puede contemplar fichaje desde el celular. En su caso, ¿qué es lo principal que te gustaría mejorar del sistema que usan hoy?
```

Para este MVP no hace falta implementar RAG o una knowledge base.

Si el sistema no tiene información suficiente para responder una pregunta comercial, debe evitar inventar información.

Puede decir que un asesor puede confirmarlo y continuar con el workflow.

## 12. Inicio de conversación

Implementá una función:

```python
start_conversation(workflow)
```

que:

1. genere el estado inicial;
2. devuelva `conversation.opening`.

En este punto NO hace falta llamar al LLM.

## 13. Persistencia

Para este MVP mantenelo simple.

Implementá una interfaz pequeña para persistencia:

```python
class ConversationStore:
    get(conversation_id)
    save(state)
```

Podés usar memoria o SQLite para la implementación inicial.

No agregues Redis, Kafka, Celery ni infraestructura innecesaria.

## 14. API

Exponé como mínimo:

```http
POST /conversations
```

Request:

```json
{
  "workflow_id": "sales_discovery"
}
```

Response:

```json
{
  "conversation_id": "...",
  "message": "Hola, soy Sofia. ¿Con quién tengo el gusto de hablar?",
  "state": {...}
}
```

Y:

```http
POST /conversations/{conversation_id}/turn
```

Request:

```json
{
  "message": "Juan, trabajo en Metalúrgica Perez."
}
```

Response:

```json
{
  "message": "Mucho gusto, Juan. ¿A qué se dedica Metalúrgica Perez?",
  "state": {...},
  "next_objective": "company_activity",
  "status": "active"
}
```

Usá FastAPI si el proyecto está en Python.

Si el repositorio existente ya usa otro stack, respetá el stack existente en lugar de introducir Python innecesariamente.

## 15. LLM provider

Encapsulá la llamada en algo pequeño:

```python
class LLMClient:
    async def process_turn(...) -> AgentTurn:
        ...
```

Si el proyecto ya tiene integración con OpenAI-compatible APIs, utilizala.

Debe funcionar con un endpoint OpenAI compatible para poder utilizar posteriormente modelos locales.

Configuración por environment variables, por ejemplo:

```text
LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
```

Usá structured outputs si el provider/model lo soporta.

Si no lo soporta, solicitá JSON y validalo posteriormente con Pydantic.

## 16. Tests

Agregá tests para al menos estos escenarios:

### Test 1: información normal

Usuario:

```text
Juan.
```

Resultado:

```text
contact_name = Juan
```

y el siguiente objetivo debe ser `company_name`.

### Test 2: múltiples campos juntos

Usuario:

```text
Soy Juan de Acme, hacemos logística y somos unas 80 personas.
```

Debe poder actualizar:

```text
contact_name
company_name
company_activity
employee_count
```

en un solo turno.

### Test 3: información ambigua

Usuario:

```text
Somos bastantes.
```

No debe completar `employee_count`.

### Test 4: usuario se adelanta

Si proporciona información correspondiente a campos posteriores, esos campos deben quedar completados y no deben preguntarse nuevamente.

### Test 5: required_if

Si:

```text
wants_demo = false
```

`email` no debe impedir completar el workflow.

Si:

```text
wants_demo = true
```

`email` debe ser obligatorio.

### Test 6: protección contra campos inventados

Si el modelo devuelve:

```json
{
  "field_updates": {
    "random_field": "foo"
  }
}
```

la aplicación debe rechazar o ignorar ese campo.

### Test 7: completed

El modelo no puede terminar arbitrariamente el workflow.

`status = completed` debe establecerse finalmente según:

```python
is_workflow_complete(...)
```

## 17. Fuera de scope

NO implementar todavía:

* editor visual de workflows;
* múltiples agentes;
* RAG;
* vector database;
* memoria semántica;
* FSM compleja;
* branches arbitrarios;
* lenguaje de condiciones;
* analytics;
* CRM;
* scheduling;
* tool calls reales;
* STT;
* TTS;
* LiveKit;
* Asterisk;
* authentication;
* frontend.

Quiero aislar primero y validar el motor conversacional.

## 18. Estructura deseada

Mantené el proyecto pequeño.

Algo similar a:

```text
app/
  main.py

  workflows/
    sales_discovery.yml

  conversation/
    models.py
    workflow.py
    engine.py
    store.py

  llm/
    client.py
    prompt.py

tests/
  test_workflow.py
  test_engine.py
```

No sigas esta estructura si el repositorio existente tiene convenciones diferentes.

Primero inspeccioná el repositorio y adaptate a él.

## 19. Criterio principal

La característica central que quiero validar es esta:

El chatbot no sigue:

```text
pregunta 1
pregunta 2
pregunta 3
pregunta 4
```

Sino que mantiene:

```text
información conocida
+
objetivos pendientes
+
contexto del último mensaje
```

y el LLM determina cuál es la mejor continuación conversacional.

El YAML define objetivos y restricciones.

El LLM maneja la conversación.

La aplicación mantiene y valida el estado.

## 20. Entrega

Implementá el código completo del MVP.

Después de implementarlo:

1. Mostrame brevemente la estructura creada.
2. Explicá el flujo de un turno desde que llega el mensaje hasta que se devuelve la respuesta.
3. Indicá cómo agregar un nuevo workflow YAML.
4. Mostrá cómo ejecutar los tests.
5. Mostrá un ejemplo de conversación de 4-5 turnos.
6. No agregues funcionalidades fuera del scope sin una razón concreta.

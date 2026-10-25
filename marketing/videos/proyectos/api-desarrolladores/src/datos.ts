// Pedidos y respuestas que se muestran en pantalla. Salen de pedidos reales del 25-oct-2026 contra
// https://app.atentina.com.ar (cliente atentina; salidas en scratch/videos/api-desarrolladores/), recortados.
// La key va enmascarada. La conversación de GET /calls/{id} es real y está anonimizada (nombre, empresa y teléfono).

export const BASE = "https://app.atentina.com.ar/api/v1/inference";
export const API = "https://app.atentina.com.ar/api/v1";

// Exactamente el script que se corrió (llm_pantalla.py)
export const PY_LLM = `import os
from openai import OpenAI

client = OpenAI(
    base_url="https://app.atentina.com.ar/api/v1/inference",
    api_key=os.environ["ATENTINA_KEY"],   # vaas_••••
)
SISTEMA = ("Sos el asistente de una veterinaria. Horario: lunes "
           "a viernes de 9 a 19 y sábados de 9 a 13. Respondé en una frase.")
chat = client.chat.completions.create(
    model="atentina",  # obligatorio, pero se ignora
    messages=[{"role": "system", "content": SISTEMA},
              {"role": "user", "content": "¿Atienden los sábados?"}],
    max_tokens=60,
)
print(chat.choices[0].message.content)
print(chat.usage.prompt_tokens, chat.usage.completion_tokens)`;

export const LLM_OUT = ["Sí, atendemos los sábados de 9 a 13 horas.", "65 17"];

export const CURL_TTS = `curl ${BASE}/audio/speech \\
  -H "Authorization: Bearer $ATENTINA_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"voice": "sofia",
       "input": "Sí, atendemos los sábados de 9 a 13 horas."}' \\
  --output respuesta.wav`;

// GET /agents/{id} del agente Turnos (demo de la landing), recortado
export const AGENT = `{
  "id": "e825954e-e163-…",
  "name": "Turnos",
  "engine": "classic",
  "version": 2,
  "voice": "sofia",
  "definition": {
    "agent": { "name": "Sofía", "language": "es-AR" },
    "fields": {
      "especialidad": { "type": "choice", "required": true },
      "turno":        { "type": "string", "required": true },
      "nombre":       { "type": "string", "required": true },
      "dni":          { "type": "string", "required": true },
      "obra_social":  { "type": "string", "required": false },
      "confirma":     { "type": "boolean", "required": true }
    }
  }
}`;

// Llamada telefónica: el ejemplo de la documentación (no se corrió: llamaría a un número real)
export const CALL_PHONE = `{
  "agent_id": "e825954e-e163-…",
  "phone": "+5493515551234"
}`;

// La que se corrió: sin phone, llamada de prueba (no llama a nadie; se cortó con /hangup)
export const CALL_TEST = `{
  "agent_id": "e825954e-e163-…"
}`;

export const CALL_OUT = `{
  "conversation_id": "2465c035-178f-…",
  "room": "call-2465c035-178f-…",
  "mode": "prueba",
  "join_url": "https://meet.livekit.io/custom?…"
}`;

// GET /calls/{conversation_id} de una llamada entrante real del 20-oct-2026, anonimizada y recortada
export const CALL_DETAIL = `{
  "id": "42f6c59d-57f6-…",
  "agent_name": "Atentina Comercial",
  "call": {
    "mode": "entrante",
    "status": "finalizada",
    "duration_seconds": 95,
    "ended_reason": "customer_hangup"
  },
  "outcome": { "label": "Interesado sin reunión", "goal": false },
  "fields": [
    { "name": "contact_name",  "value": "Martín" },
    { "name": "company_name",  "value": "Empresa Ejemplo" },
    { "name": "wants_meeting", "value": false },
    { "name": "dato_5",        "value": "351 ••• ••••" }
  ]
}`;

// Código de ejemplo del lado del integrador (ilustrativo: guardar en su CRM)
export const PY_USO = `r = requests.get(f"{API}/calls/{conversation_id}",
                 headers=auth).json()
if r["call"]["status"] == "finalizada":
    datos = {c["name"]: c["value"] for c in r["fields"]}
    crm.guardar(datos, resultado=r["outcome"]["label"])`;

export const CAMPAIGN = `curl ${API}/campaigns \\
  -H "Authorization: Bearer $ATENTINA_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"channel": "voice", "name": "Mora 30 días",
       "agent_id": "…", "tags": ["mora_30"], "start": true,
       "callback_url":
         "https://tu-sistema.com.ar/atentina/webhook"}'`;

// De la documentación (sección Webhook)
export const VERIFY = `def firma_valida(cuerpo, header, secreto):
    esperada = "sha256=" + hmac.new(
        secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, header)`;

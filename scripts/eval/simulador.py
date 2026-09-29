"""El cliente de la llamada (docs/EVAL_LLM_PLAN.md, seccion 3).

  Simulador  un LLM externo (EVAL_LLM_*: DeepSeek u otro OpenAI-compatible) que
             actua la persona con su ficha. Ve la conversacion desde su lado: lo
             que dijo el agente como "user" y lo suyo como "assistant".
  Guion      respuestas fijas en orden (persona.guion), sin API externa:
             regresion gratis y determinista.

Los dos devuelven (lo que dice, si corta la llamada despues de decirlo).
"""
import json
import re
from urllib.parse import urlparse

from openai import AsyncOpenAI

# Sube cuando cambia el prompt: queda en run.json para no comparar runs con
# simuladores distintos.
PROMPT_VERSION = "1"

SYSTEM = """Sos una persona que atiende una llamada telefónica en Córdoba, Argentina. Actuás un papel: no sos un asistente, no ayudás al agente, no sos más paciente ni más claro de lo que sería esa persona.

TU PERSONA:
{estilo}

TU FICHA (lo único que sabés de vos; no inventes otros datos personales; podés negarte a darlos si tu persona lo haría):
{ficha}

CÓMO HABLÁS:
- Español rioplatense coloquial, como se habla por teléfono: una o dos frases cortas por turno, salvo que tu persona diga otra cosa.
- Los correos los dictás como se dicen por teléfono ("juan arroba gmail punto com"); los números de teléfono y DNI, en cifras o de a grupos, según tu persona.
- Respondés solo a lo último que dijo el agente. No repitas datos que ya diste salvo que te los vuelvan a pedir.
- Si el agente se despide, despedite corto y cortá.
- Si tu persona cortaría la llamada en este punto (se enoja, no tiene tiempo, ya terminó), decilo y marcá corta.
- No uses comillas, paréntesis ni acotaciones de teatro: solo lo que decís en voz alta.

Respondé siempre en JSON, así: {{"dice": "lo que decís en voz alta", "corta": false}}"""


def es_local(base_url: str) -> bool:
    """Un vLLM propio (vllm-llm, localhost, IP de la LAN) contra una API externa
    (DeepSeek, OpenRouter, ...)."""
    host = urlparse(base_url).hostname or ""
    return host in ("localhost", "vllm-llm") or "." not in host or host.startswith(("127.", "192.168.", "10."))


def opciones_llm(base_url: str) -> dict:
    """Con un vLLM propio (Qwen) hay que apagar el pensamiento: si no, se lleva los
    max_tokens y el content vuelve vacio. Las API externas no reciben el
    parametro, que es de vLLM."""
    if not es_local(base_url):
        return {}
    return {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}


class Simulador:
    nombre = "simulado"

    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.7):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=60, max_retries=3)
        self.model, self.temperature = model, temperature
        self.extra = opciones_llm(base_url)

    def system(self, escenario) -> str:
        ficha = "\n".join(f"- {k}: {v}" for k, v in escenario.ficha.items()) or "- (sin datos)"
        return SYSTEM.format(estilo=escenario.estilo, ficha=ficha)

    async def responder(self, escenario, historial: list[tuple[str, str]]) -> tuple[str, bool]:
        """historial: [("agente", texto), ("usuario", texto), ...], termina en el agente.
        Una respuesta vacia (paso con deepseek-v4.1-flash por OpenRouter: content
        vacio de forma esporadica) se reintenta; si persiste, la conversacion
        queda con error en vez de "sin terminar"."""
        messages = [{"role": "system", "content": self.system(escenario)}]
        for quien, texto in historial:
            messages.append({"role": "user" if quien == "agente" else "assistant", "content": texto})
        crudo = []
        for intento in range(3):
            r = await self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=self.temperature,
                response_format={"type": "json_object"}, max_tokens=1000 * 2 ** intento, **self.extra)
            m = r.choices[0].message
            dice, corta = parsear(m.content or "")
            if dice:
                return dice, corta
            crudo.append({"intento": intento + 1, "finish": r.choices[0].finish_reason, "content": (m.content or "")[:200],
                          "reasoning": str(getattr(m, "reasoning", None) or getattr(m, "reasoning_content", None) or "")[:200]})
        raise RuntimeError(f"simulador sin respuesta tras 3 intentos: {json.dumps(crudo, ensure_ascii=False)}")


def parsear(content: str) -> tuple[str, bool]:
    """El JSON del simulador. Vistos por OpenRouter: una lista ("[]", "[true]",
    "[{...}]") en vez del objeto, o el objeto dentro de texto. Vacio = reintentar."""
    content = content.strip()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            data = next((x for x in data if isinstance(x, dict)), None)
        if isinstance(data, dict):
            return str(data.get("dice") or "").strip(), bool(data.get("corta"))
        return "", False
    except ValueError:
        pass
    m = re.search(r'"dice"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
    if m:
        try:
            return json.loads(f'"{m.group(1)}"'), bool(re.search(r'"corta"\s*:\s*true', content))
        except ValueError:
            return m.group(1), False
    if content.startswith(("{", "[")):
        return "", False
    return content.strip('"'), False


class Guion:
    nombre = "guion"

    def __init__(self, mensajes: list[str], fallback: str = "¿Cómo? No te entendí."):
        self.mensajes, self.fallback, self.i = list(mensajes), fallback, 0

    async def responder(self, escenario, historial) -> tuple[str, bool]:
        if self.i < len(self.mensajes):
            msg = self.mensajes[self.i]
            self.i += 1
            return msg, self.i >= len(self.mensajes) and _es_despedida(msg)
        # Se acabo el guion y el agente sigue: una vez "¿cómo?", despues corta.
        self.i += 1
        return (self.fallback, False) if self.i == len(self.mensajes) + 1 else ("Bueno, chau.", True)


def _es_despedida(msg: str) -> bool:
    return bool(re.search(r"\bchau\b|\badiós\b|hasta luego", msg, re.I))

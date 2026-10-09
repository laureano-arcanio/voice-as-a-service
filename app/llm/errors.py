"""Errores del LLM con tipo, para que voz y WhatsApp respondan algo en lugar de quedar
mudos (H11). LLMClient traduce a estos los errores de red, de vLLM y de formato;
ConversationEngine.process_turn los propaga sin guardar el turno."""


class LLMError(Exception):
    """El LLM no dio una respuesta usable (caido, 5xx, 400, salida invalida o deadline).

    spoken: el texto que ya salio por on_message antes de fallar (streaming): la voz
    ya lo dijo, y sabe si la frase de respaldo va sola o despues de eso."""

    kind = "error"

    def __init__(self, message: str, *, spoken: str = ""):
        super().__init__(message)
        self.spoken = spoken


class LLMContextError(LLMError):
    """El pedido no entra en el contexto del modelo (LLM_CONTEXT_TOKENS): la definicion
    del agente mas el mensaje nuevo ya se pasan, o vLLM respondio 400 por longitud."""

    kind = "context"


class LLMTimeoutError(LLMError):
    """Se paso el deadline del pedido entero (LLM_TURN_DEADLINE_SECONDS o el de la
    extraccion), o el timeout de red del cliente."""

    kind = "timeout"

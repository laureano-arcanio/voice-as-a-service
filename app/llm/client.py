from openai import AsyncOpenAI

from app import config

from app.conversation.models import AgentTurn, ConversationState, Workflow

from .prompt import SYSTEM_PROMPT, build_user_prompt

TYPE_SCHEMAS = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "email": {"type": "string"},
    "email_or_phone": {"type": "string"},
}


def field_schema(spec) -> dict:
    base = {"type": "string", "enum": spec.options} if spec.type == "choice" else TYPE_SCHEMAS[spec.type]
    return {"anyOf": [base, {"type": "null"}]}


def turn_schema(workflow: Workflow) -> dict:
    return {
        "type": "object",
        "properties": {
            "field_updates": {
                "type": "object",
                "properties": {name: field_schema(spec) for name, spec in workflow.fields.items()},
                "additionalProperties": False,
            },
            "next_objective": {"anyOf": [{"type": "string", "enum": list(workflow.fields)}, {"type": "null"}]},
            "assistant_message": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "completed"]},
        },
        "required": ["field_updates", "next_objective", "assistant_message", "status"],
        "additionalProperties": False,
    }


# Recomendados por Qwen: con pensamiento, 0.6 / 0.95 / 20; sin pensamiento, 0.7 / 0.8 / 20.
# Qwen desaconseja temperaturas bajas o greedy con pensamiento (se repite).
SAMPLING = {
    True: {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0},
    False: {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0},
}


def request_options(thinking: bool, budget: int, temperature: float | None = None) -> dict:
    sampling = dict(SAMPLING[thinking])
    if temperature is not None:
        sampling["temperature"] = temperature
    extra = {"top_k": sampling.pop("top_k"), "min_p": sampling.pop("min_p"),
             "chat_template_kwargs": {"enable_thinking": thinking}}
    if thinking:
        extra["thinking_token_budget"] = budget
    return {**sampling, "extra_body": extra}


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, thinking: bool = config.LLM_THINKING,
                 thinking_budget: int = config.LLM_THINKING_BUDGET, temperature: float | None = config.LLM_TEMPERATURE):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=30)
        self.model = model
        self.options = request_options(thinking, thinking_budget, temperature)

    async def process_turn(self, workflow: Workflow, state: ConversationState, user_message: str) -> AgentTurn:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(workflow, state, user_message)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "agent_turn", "schema": turn_schema(workflow), "strict": True},
            },
            **self.options,
        )
        message = response.choices[0].message
        turn = AgentTurn.model_validate_json(message.content)
        turn.raw = message.content
        # vLLM separa el razonamiento (--reasoning-parser qwen3).
        turn.reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        return turn

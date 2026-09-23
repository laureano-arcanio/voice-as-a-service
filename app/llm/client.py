from openai import AsyncOpenAI

from app.conversation.models import AgentTurn, ConversationState, Workflow

from .prompt import SYSTEM_PROMPT, build_user_prompt

TYPE_SCHEMAS = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "email": {"type": "string"},
}


def turn_schema(workflow: Workflow) -> dict:
    return {
        "type": "object",
        "properties": {
            "field_updates": {
                "type": "object",
                "properties": {name: {"anyOf": [TYPE_SCHEMAS[spec.type], {"type": "null"}]} for name, spec in workflow.fields.items()},
                "additionalProperties": False,
            },
            "next_objective": {"anyOf": [{"type": "string", "enum": list(workflow.fields)}, {"type": "null"}]},
            "assistant_message": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "completed"]},
        },
        "required": ["field_updates", "next_objective", "assistant_message", "status"],
        "additionalProperties": False,
    }


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=30)
        self.model = model

    async def process_turn(self, workflow: Workflow, state: ConversationState, user_message: str) -> AgentTurn:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(workflow, state, user_message)},
            ],
            temperature=0.2,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "agent_turn", "schema": turn_schema(workflow), "strict": True},
            },
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return AgentTurn.model_validate_json(response.choices[0].message.content)

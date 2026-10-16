"""Catalogo de parametros de generacion del LLM para el editor del agente (app/llm/params.py):
los de cada proveedor y los del LLM local, que dependen de la familia del modelo y del motor."""
from fastapi import APIRouter

from ...config import settings
from ...llm.client import SAMPLING, sampling_family
from ...llm.params import CATALOG, PROVIDER_LABELS, for_provider
from ..deps import UserPrincipal
from ..schemas import LlmParamsOut, LlmParamSpec, LlmProviderSpec

router = APIRouter(prefix="/llm", tags=["llm"])


def _local_defaults(engine: str) -> dict:
    """Lo que manda el servidor propio si el agente no toca nada: el muestreo de la familia del
    modelo y el razonamiento por motor (voz apagado; assistant prendido, con su tope por paso)."""
    family = sampling_family(settings.vllm_llm_model)
    if engine == "assistant":
        thinking, budget = settings.assistant_thinking, settings.assistant_thinking_budget
        extra = {"max_tokens": settings.assistant_max_step_tokens}
    else:
        thinking, budget = settings.llm_thinking, settings.llm_thinking_budget
        extra = {}
    sampling = SAMPLING[family][thinking]
    return {
        "temperature": settings.llm_temperature if settings.llm_temperature is not None else sampling["temperature"],
        "top_p": sampling["top_p"], "top_k": sampling["top_k"], "min_p": sampling["min_p"],
        "enable_thinking": thinking, "thinking_token_budget": budget, **extra,
    }


@router.get("/params", response_model=LlmParamsOut)
def llm_params(p: UserPrincipal):
    """El catalogo, por proveedor, con los defaults del LLM local por motor. Solo lectura."""
    providers = [
        LlmProviderSpec(kind=kind, label=PROVIDER_LABELS[kind],
                        params=[LlmParamSpec(name=par.name, label=par.label, type=par.type,
                                             minimum=par.minimum, maximum=par.maximum,
                                             choices=list(par.choices), hint=par.hint)
                                for par in for_provider(kind)])
        for kind in (k for k in CATALOG["temperature"].providers)
    ]
    return LlmParamsOut(
        local_model=settings.vllm_llm_model,
        local_family=sampling_family(settings.vllm_llm_model),
        local_defaults={"classic": _local_defaults("classic"), "assistant": _local_defaults("assistant")},
        providers=providers)

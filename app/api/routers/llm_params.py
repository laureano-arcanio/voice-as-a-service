"""Catalogo de parametros de generacion del LLM para el editor del agente (app/llm/params.py):
los de cada proveedor y los del LLM local (su configuracion)."""
from fastapi import APIRouter

from ...config import settings
from ...llm.params import CATALOG, PROVIDER_LABELS, for_provider
from ..deps import UserPrincipal
from ..schemas import LlmParamsOut, LlmParamSpec, LlmProviderSpec

router = APIRouter(prefix="/llm", tags=["llm"])


def _local_defaults() -> dict:
    """Lo que manda el servidor propio si el agente no toca nada: la configuracion del modelo (LLM_* del .env o
    del override del modelo). Lo que no esta definido lo decide el servidor."""
    sampling = {"temperature": settings.llm_temperature, "top_p": settings.llm_top_p, "top_k": settings.llm_top_k,
                "min_p": settings.llm_min_p}
    return {**{k: v for k, v in sampling.items() if v is not None}, "enable_thinking": settings.llm_thinking,
            "thinking_token_budget": settings.llm_thinking_budget}


@router.get("/params", response_model=LlmParamsOut)
def llm_params(p: UserPrincipal):
    """El catalogo, por proveedor, con los defaults del LLM local. Solo lectura."""
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
        local_defaults=_local_defaults(),
        providers=providers)

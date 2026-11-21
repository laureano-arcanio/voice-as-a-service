"""Parches mínimos para correr Qwen-Image-2.1 GGUF en vLLM-Omni 0.32.

1) ComponentQuantizationConfig: vllm-gguf-plugin 0.0.5 solo mira un
   quantization_config plano; se le hace resolver el slice ``transformer`` para
   poder combinar GGUF (DiT) con FP8 online (text encoder).
2) ``DiffusionGGUFLinearMethod.apply`` concatena los shards QKV con
   ``torch.cat(result, axis=1)``, que en tensores 3-D (batch, tokens, hidden)
   concatena sobre la dimensión de tokens. Se reimplementa con ``dim=-1``.
3) Diagnóstico opcional con QWEN21_DEBUG=1.
"""

import torch
from vllm_gguf_plugin.weights_adapter.diffusion import integration as _i

_is_gguf = _i.is_gguf_quant_config
_get_gguf_model = _i.get_gguf_model_from_config
_extend_unquantized = _i._extend_unquantized_modules


def _transformer_slice(cfg):
    get_name = getattr(cfg, "get_name", None)
    if get_name is not None and get_name() == "component" and hasattr(cfg, "resolve"):
        return cfg.resolve("transformer")
    return cfg


_i.is_gguf_quant_config = lambda cfg: _is_gguf(_transformer_slice(cfg))
_i.get_gguf_model_from_config = lambda cfg: _get_gguf_model(_transformer_slice(cfg))
_i._extend_unquantized_modules = lambda cfg, names: _extend_unquantized(
    _transformer_slice(cfg), names
)


import vllm_gguf_plugin.quantization.diffusion_config as _dc  # noqa: E402


def _apply_with_last_dim_cat(self, layer, x, bias=None):
    shard_id = getattr(layer.qweight, "shard_id", [])
    qweight = layer.qweight
    if shard_id:
        shard_id = ["q", "k", "v"] if "q" in shard_id else shard_id
        fallback = getattr(layer.qweight_type, "weight_type", None)
        if fallback is None:
            fallback = next(iter(layer.qweight_type.shard_weight_type.values()))
        types = [layer.qweight_type.shard_weight_type.get(i, fallback) for i in shard_id]
        if len(set(types)) == 1:
            out = _dc.dequant_gemm_gguf(x, qweight, types[0])
            if bias is not None:
                out.add_(bias)
            return out
        result = []
        for idx in shard_id:
            start, end, width = layer.qweight.shard_offset_map[idx]
            qtype = layer.qweight_type.shard_weight_type.get(idx, fallback)
            result.append(
                _dc.dequant_gemm_gguf(x, qweight[start:end, :width].contiguous(), qtype)
            )
        out = torch.cat(result, dim=-1)
    else:
        out = _dc.dequant_gemm_gguf(
            x, qweight, layer.qweight_type.weight_type
        )
    if bias is not None:
        out.add_(bias)
    return out


_dc.DiffusionGGUFLinearMethod.apply = _apply_with_last_dim_cat

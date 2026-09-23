"""Utilidades compartidas: modelos del HF cache del proyecto (offline) y rutas por defecto."""
import os

TTS_BASE = {"1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-Base", "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-Base"}
ASR = "Qwen/Qwen3-ASR-1.7B"


def local_model(name):
    """Ruta local de un modelo: una carpeta existente, o un repo id resuelto en el HF cache (offline)."""
    if os.path.isdir(name):
        return name
    from huggingface_hub import snapshot_download
    return snapshot_download(name, local_files_only=True)

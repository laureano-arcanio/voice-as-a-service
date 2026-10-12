"""Archivos (imagen o PDF) que un operador le manda a su asistente (contrato v1.1, docs/APPS_PLAN.md):
OCR en la CPU de app (tesseract spa; un PDF, su primera pagina con pdftoppm), sin tocar las GPUs. El
texto entra al turno con el sha256 del archivo; que significa (un comprobante, una planilla) lo decide
la app con sus herramientas, que pueden usar el hash para detectar el mismo archivo repetido.
"""
import asyncio
import hashlib
import shutil

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 2500
TIMEOUT = 30
MARK = "[archivo recibido · sha256 {hash}]"


class AttachmentError(Exception):
    pass


def available() -> bool:
    return shutil.which("tesseract") is not None


async def _run(args: list[str], data: bytes) -> bytes:
    proc = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(data), TIMEOUT)
    except TimeoutError:
        proc.kill()
        raise AttachmentError("el OCR tardó demasiado") from None
    if proc.returncode != 0:
        raise AttachmentError(f"{args[0]} salió con {proc.returncode}")
    return out


async def read(data: bytes, mime: str) -> str:
    """Texto del archivo (imagen o PDF)."""
    if not available():
        raise AttachmentError("tesseract no está instalado")
    if len(data) > MAX_BYTES:
        raise AttachmentError("archivo muy grande")
    image = data
    if mime.startswith("application/pdf"):
        if shutil.which("pdftoppm") is None:
            raise AttachmentError("pdftoppm no está instalado")
        image = await _run(["pdftoppm", "-png", "-r", "200", "-f", "1", "-l", "1", "-", "-"], data)
    text = (await _run(["tesseract", "stdin", "stdout", "-l", "spa", "--psm", "4"], image)).decode("utf-8", "ignore")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)[:MAX_CHARS]


def turn_text(data: bytes, text: str, caption: str | None) -> str:
    head = MARK.format(hash=hashlib.sha256(data).hexdigest())
    parts = [head]
    if caption:
        parts.append(f"Texto del mensaje: {caption.strip()}")
    parts.append("Texto leído del archivo (OCR, puede tener errores):\n" + (text or "(no se pudo leer texto)"))
    return "\n".join(parts)

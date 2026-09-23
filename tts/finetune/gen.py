"""Genera audios de evaluacion con un modelo Qwen3-TTS (ver docs/TTS_FINETUNE.md).

Juegos de frases (--set):
- eval: las frases de eval de la voz (no entrenadas, hay grabacion real) + DOMAIN.
- llamada: eval_llamada.json, las 28 oraciones del agente en una llamada real (llamada 120),
  una por request como las manda el agente. Sirve para medir pausas entre oraciones.

Modos: --mode custom (checkpoint fine-tuneado, voz por nombre) o --mode clone (Base
zero-shot con ref.wav + ref.txt, como la voz clonada de produccion).
Salida: <out>/<nombre>.wav + meta.json.
"""
import argparse
import json
import time
from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

from common import local_model

DOMAIN = [
    "Hola, buen día. Te llamo de la clínica para confirmar tu turno del jueves a las diez y media.",
    "¿Me podés decir tu número de documento, por favor?",
    "Perfecto, ya quedó registrado. ¿Necesitás algo más?",
    "Disculpá, no te escuché bien. ¿Me lo repetís?",
    "El total es de cuarenta y dos mil quinientos pesos, con vencimiento el quince de octubre.",
    "Gracias por comunicarte. Que tengas una muy buena tarde.",
    "Te confirmo la dirección: avenida Corrientes mil doscientos cuarenta, tercer piso, departamento B.",
    "¿El teléfono de contacto sigue siendo el once, cuatro cinco seis siete, ocho nueve cero uno?",
    "Mirá, el sistema me dice que la factura ya está paga desde el martes.",
    "Si querés, te paso con un asesor para que lo vean juntos.",
    "Bárbaro. Entonces te agendo para el lunes veintiocho a las nueve de la mañana.",
    "Uy, perdón, se cortó un poquito. ¿Seguís ahí?",
    "Para continuar, necesito que me confirmes tu fecha de nacimiento.",
    "No hay problema, lo podemos reprogramar para la semana que viene.",
    "El médico de guardia es el doctor Fernández, atiende hasta las ocho de la noche.",
    "Tu pedido sale mañana y llega entre el jueves y el viernes.",
    "¿Preferís que te mandemos el comprobante por mail o por WhatsApp?",
    "Listo, ya te envié el link de pago. Tiene validez por cuarenta y ocho horas.",
    "Entiendo que es molesto, voy a hacer lo posible para resolverlo hoy mismo.",
    "La cuota de este mes es de dieciocho mil trescientos veinte pesos.",
    "¿Me deletreás el apellido, por favor?",
    "Anotá el número de gestión: cuatro, siete, dos, nueve, cinco.",
    "Lamentablemente, ese horario ya está ocupado. ¿Te sirve a las once y cuarto?",
    "Perfecto, cualquier cosa nos volvés a llamar. ¡Chau, que andes bien!",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="checkpoint o repo id")
    ap.add_argument("--mode", choices=["clone", "custom"], default="custom")
    ap.add_argument("--speaker", help="nombre de la voz del checkpoint (--mode custom)")
    ap.add_argument("--data", required=True, help="carpeta de la voz (eval.jsonl, ref.wav, ref.txt)")
    ap.add_argument("--set", choices=["eval", "llamada"], default="eval")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--language", default="Auto",
                    help="Auto = prefijo sin idioma, el mismo que usa el entrenamiento y el agente")
    args = ap.parse_args()

    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.set == "llamada":
        texts = [tuple(x) for x in json.load(open(Path(__file__).with_name("eval_llamada.json"), encoding="utf-8"))]
    else:
        items = [json.loads(l) for l in open(data / "eval.jsonl", encoding="utf-8")]
        texts = [(r["utt"], r["text"]) for r in items] + [(f"dom_{i:02d}", t) for i, t in enumerate(DOMAIN)]

    tts = Qwen3TTSModel.from_pretrained(local_model(args.model), device_map="cuda:0", dtype=torch.bfloat16,
                                        attn_implementation="flash_attention_2")
    prompt = None
    if args.mode == "clone":
        prompt = tts.create_voice_clone_prompt(ref_audio=str(data / "ref.wav"),
                                               ref_text=(data / "ref.txt").read_text(encoding="utf-8"))
    meta = []
    for name, text in texts:
        torch.manual_seed(args.seed)
        t0 = time.time()
        if args.mode == "clone":
            wavs, sr = tts.generate_voice_clone(text=text, language=args.language, voice_clone_prompt=prompt,
                                                max_new_tokens=1024)
        else:
            wavs, sr = tts.generate_custom_voice(text=text, speaker=args.speaker, language=args.language,
                                                 max_new_tokens=1024)
        sf.write(out / f"{name}.wav", wavs[0], sr)
        meta.append({"name": name, "text": text, "dur": len(wavs[0]) / sr, "gen_s": round(time.time() - t0, 2)})
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}: {len(meta)} audios, {sum(m['dur'] for m in meta):.0f} s de audio en "
          f"{sum(m['gen_s'] for m in meta):.0f} s")


if __name__ == "__main__":
    main()

"""SFT de una voz sobre Qwen3-TTS-12Hz-*-Base (ver docs/TTS_FINETUNE.md).

Basado en finetuning/sft_12hz.py de QwenLM/Qwen3-TTS con las correcciones de
zhyuan11/Qwen3-TTS-Finetuning, mas:
- text_projection sobre el embedding de texto (sin ella el modelo genera ruido, issue #39).
- sin doble shift de labels: el loss de HF ya desplaza (issue #179, la voz se acelera
  epoca a epoca). El loss del sub-talker se recalcula aca porque qwen_tts 0.1.1 tambien
  lo re-desplaza.
- --sr: AdamW con redondeo estocastico a bf16. Con pesos bf16 y lr 2e-6, AdamW comun
  redondea a cero ~95% de los updates (medido con --probe: 4,7% de pesos cambiados contra
  22,8% con --sr, 10 steps).
- embedding de texto (311 M params) y speaker encoder congelados: 1,61 B entrenables en
  1.7B, 17 GB de VRAM con batch 2.
- log de loss a JSONL y checkpoints solo en las epocas pedidas.

Salida: <output>/checkpoint-epoch-N/ (tipo custom_voice, la voz va por nombre) y train_log.jsonl.

Varias voces en un checkpoint: --speaker_name y --train_jsonl con listas separadas por comas,
en el mismo orden. Cada voz queda con su id (3000, 3001, ...) y el embedding de su ref.wav.
"""
import argparse
import json
import math
import os
import shutil
import time

import torch
import torch.nn.functional as F
from accelerate import Accelerator
from safetensors.torch import save_file
from torch.utils.data import DataLoader
from transformers import AutoConfig

from common import local_model
from dataset import TTSDataset
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel


class AdamWSR(torch.optim.Optimizer):
    """AdamW con estados en el dtype del parametro y redondeo estocastico al escribir bf16."""

    def __init__(self, params, lr, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.01):
        super().__init__(params, dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay))

    @staticmethod
    def _sr_bf16(x32):
        noise = torch.randint_like(x32, 0, 1 << 16, dtype=torch.int32)
        return ((x32.view(torch.int32) + noise) & -65536).view(torch.float32).to(torch.bfloat16)

    @torch.no_grad()
    def step(self, closure=None):
        for g in self.param_groups:
            b1, b2 = g["betas"]
            for p in g["params"]:
                if p.grad is None:
                    continue
                st = self.state[p]
                if not st:
                    st["t"] = 0
                    st["m"] = torch.zeros_like(p, dtype=torch.float32 if p.numel() < 4096 else p.dtype)
                    st["v"] = torch.zeros_like(p, dtype=torch.float32 if p.numel() < 4096 else p.dtype)
                st["t"] += 1
                t = st["t"]
                grad = p.grad.float()
                m = st["m"].float().mul_(b1).add_(grad, alpha=1 - b1)
                v = st["v"].float().mul_(b2).addcmul_(grad, grad, value=1 - b2)
                st["m"].copy_(m)
                st["v"].copy_(v)
                upd = (m / (1 - b1 ** t)) / ((v / (1 - b2 ** t)).sqrt_().add_(g["eps"]))
                new = p.float().mul_(1 - g["lr"] * g["weight_decay"]).add_(upd, alpha=-g["lr"])
                p.copy_(self._sr_bf16(new) if p.dtype == torch.bfloat16 else new)


class VoiceBatches:
    """Batches de una sola voz, en orden aleatorio: collate_fn concatena los ref.wav del batch, que
    tienen que medir lo mismo. Con una voz equivale a shuffle=True."""

    def __init__(self, bounds, batch_size):
        self.bounds, self.bs = bounds, batch_size

    def __iter__(self):
        batches = []
        for a, b in self.bounds:
            idx = (torch.randperm(b - a) + a).tolist()
            batches += [idx[i:i + self.bs] for i in range(0, len(idx), self.bs)]
        return iter([batches[i] for i in torch.randperm(len(batches)).tolist()])

    def __len__(self):
        return sum(math.ceil((b - a) / self.bs) for a, b in self.bounds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init_model_path", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base", help="repo id o carpeta")
    ap.add_argument("--output_model_path", required=True)
    ap.add_argument("--train_jsonl", required=True, help="uno por voz, separados por comas")
    ap.add_argument("--batch_size", type=int, default=2)
    ap.add_argument("--grad_accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-6)
    ap.add_argument("--warmup_steps", type=int, default=0, help="optimizer steps de warmup lineal")
    ap.add_argument("--num_epochs", type=int, default=10)
    ap.add_argument("--save_epochs", default="", help="lista separada por comas (default: todas)")
    ap.add_argument("--speaker_name", required=True, help="uno por voz, separados por comas")
    ap.add_argument("--sr", action="store_true", help="AdamW con redondeo estocastico")
    ap.add_argument("--probe", type=int, default=0, help="cortar tras N optimizer steps y medir pesos cambiados")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--train_text_embedding", action="store_true",
                    help="entrenar tambien el embedding de texto (311 M params, vocab 152k)")
    args = ap.parse_args()

    args.init_model_path = local_model(args.init_model_path)
    torch.manual_seed(args.seed)
    os.makedirs(args.output_model_path, exist_ok=True)
    log = open(os.path.join(args.output_model_path, "train_log.jsonl"), "a")
    save_epochs = {int(e) for e in args.save_epochs.split(",") if e.strip()}

    acc = Accelerator(gradient_accumulation_steps=args.grad_accum, mixed_precision="bf16")
    qwen3tts = Qwen3TTSModel.from_pretrained(args.init_model_path, torch_dtype=torch.bfloat16,
                                             attn_implementation="flash_attention_2")
    config = AutoConfig.from_pretrained(args.init_model_path)
    names = [n.strip().lower() for n in args.speaker_name.split(",")]
    jsonls = args.train_jsonl.split(",")
    assert len(names) == len(jsonls), "--speaker_name y --train_jsonl tienen que tener el mismo largo"
    data, first = [], []
    for j in jsonls:
        first.append(len(data))
        data += [json.loads(l) for l in open(j)]
    ds = TTSDataset(data, qwen3tts.processor, config)
    bounds = list(zip(first, first[1:] + [len(data)]))
    acc.print(f"voces: {dict(zip(names, [b - a for a, b in bounds]))}")
    dl = DataLoader(ds, batch_sampler=VoiceBatches(bounds, args.batch_size), collate_fn=ds.collate_fn,
                    num_workers=2)

    frozen = ("speaker_encoder",) + (() if args.train_text_embedding else ("talker.model.text_embedding",))
    for n, p in qwen3tts.model.named_parameters():
        if n.startswith(frozen):
            p.requires_grad_(False)
    params = [p for p in qwen3tts.model.parameters() if p.requires_grad]
    n_train = sum(p.numel() for p in params)
    acc.print(f"params entrenables: {n_train/1e9:.3f} B")
    opt = AdamWSR(params, lr=args.lr) if args.sr else torch.optim.AdamW(params, lr=args.lr, weight_decay=0.01)
    total_opt_steps = math.ceil(len(dl) / args.grad_accum) * args.num_epochs
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / args.warmup_steps) if args.warmup_steps else 1.0)
    model, opt, dl = acc.prepare(qwen3tts.model, opt, dl)

    snap = None
    if args.probe:
        snap = {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}

    model.train()
    # Embedding de cada voz: el speaker encoder sobre su ref.wav, en modo train como en el loop
    # (tiene BatchNorm). Todos los clips de una voz usan el mismo ref.wav.
    with torch.no_grad():
        target_spk = [model.speaker_encoder(ds[i]["ref_mel"].to(model.device).to(model.dtype))[0]
                      for i in first]
    opt_steps, t0 = 0, time.time()
    for epoch in range(args.num_epochs):
        ep_loss, ep_n = 0.0, 0
        for step, batch in enumerate(dl):
            with acc.accumulate(model):
                input_ids = batch["input_ids"]
                codec_ids = batch["codec_ids"]
                codec_mask = batch["codec_mask"]
                spk = model.speaker_encoder(batch["ref_mels"].to(model.device).to(model.dtype)).detach()
                txt = model.talker.text_projection(model.talker.model.text_embedding(input_ids[:, :, 0]))
                emb = txt * batch["text_embedding_mask"]
                cod = model.talker.model.codec_embedding(input_ids[:, :, 1]) * batch["codec_embedding_mask"]
                cod[:, 6, :] = spk
                emb = emb + cod
                for i in range(1, 16):
                    e = model.talker.code_predictor.get_input_embeddings()[i - 1](codec_ids[:, :, i])
                    emb = emb + e * codec_mask.unsqueeze(-1)
                out = model.talker(inputs_embeds=emb, attention_mask=batch["attention_mask"],
                                   labels=batch["codec_0_labels"], output_hidden_states=True)
                hs = out.hidden_states[0][-1]
                tmask = codec_mask[:, 1:]
                tgt = codec_ids[:, 1:][tmask]
                # El loss que devuelve qwen_tts 0.1.1 re-desplaza labels ya alineados (ForCausalLMLoss):
                # se recalcula directo sobre los logits.
                sub_logits, _ = model.talker.forward_sub_talker_finetune(tgt, hs[:, :-1][tmask])
                sub_loss = F.cross_entropy(sub_logits.reshape(-1, sub_logits.shape[-1]).float(),
                                           tgt[:, 1:].reshape(-1))
                loss = out.loss + 0.3 * sub_loss
                acc.backward(loss)
                if acc.sync_gradients:
                    acc.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step() if acc.sync_gradients else None
                opt.zero_grad()
            ep_loss += loss.item()
            ep_n += 1
            if acc.sync_gradients:
                opt_steps += 1
                rec = {"epoch": epoch, "step": step, "opt_step": opt_steps, "loss": round(loss.item(), 4),
                       "talker": round(out.loss.item(), 4), "sub": round(sub_loss.item(), 4),
                       "lr": sched.get_last_lr()[0], "t": round(time.time() - t0, 1),
                       "mem_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2)}
                log.write(json.dumps(rec) + "\n")
                log.flush()
                if opt_steps % 5 == 0:
                    acc.print(rec)
                if args.probe and opt_steps >= args.probe:
                    changed = tot = 0
                    for n, p in model.named_parameters():
                        if n in snap:
                            changed += (p.detach() != snap[n]).sum().item()
                            tot += p.numel()
                    acc.print(f"PROBE sr={args.sr} lr={args.lr}: {opt_steps} steps, pesos cambiados "
                              f"{changed/tot*100:.3f}% de {tot/1e9:.2f} B, mem max "
                              f"{torch.cuda.max_memory_allocated()/2**30:.1f} GB")
                    return
        acc.print(f"== epoca {epoch}: loss media {ep_loss/ep_n:.4f} ({time.time()-t0:.0f} s)")
        log.write(json.dumps({"epoch_end": epoch, "loss_mean": round(ep_loss / ep_n, 4)}) + "\n")
        log.flush()

        if acc.is_main_process and (not save_epochs or epoch in save_epochs):
            out_dir = os.path.join(args.output_model_path, f"checkpoint-epoch-{epoch}")
            top = os.path.realpath(args.init_model_path)
            shutil.copytree(args.init_model_path, out_dir, dirs_exist_ok=True,
                            ignore=lambda d, names: ["model.safetensors"] if os.path.realpath(d) == top else [])
            cfg = json.load(open(os.path.join(args.init_model_path, "config.json"), encoding="utf-8"))
            cfg["tts_model_type"] = "custom_voice"
            cfg["talker_config"]["spk_id"] = {n: 3000 + i for i, n in enumerate(names)}
            cfg["talker_config"]["spk_is_dialect"] = {n: False for n in names}
            json.dump(cfg, open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            sd = {k: v.detach().to("cpu") for k, v in acc.unwrap_model(model).state_dict().items()
                  if not k.startswith("speaker_encoder")}
            w = sd["talker.model.codec_embedding.weight"]
            for i, e in enumerate(target_spk):
                w[3000 + i] = e.to("cpu").to(w.dtype)
            save_file(sd, os.path.join(out_dir, "model.safetensors"))
            acc.print(f"guardado {out_dir}")


if __name__ == "__main__":
    main()

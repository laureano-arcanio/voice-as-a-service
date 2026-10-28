#!/usr/bin/env python3
"""Genera la config de Prometheus y Alertmanager desde el .env (`make monitoring-config`).

Escribe deploy/monitoring/generated/ (no versionado): prometheus.yml, alertmanager.yml y app_token
(el MONITORING_TOKEN con el que Prometheus lee /internal/metrics de app). Si falta
MONITORING_TOKEN en .env, lo crea y lo agrega al final (no toca ninguna otra línea).
Las alertas van a ntfy (ALERT_NTFY_TOPIC): critical con prioridad alta (suena) y warning con
prioridad baja (sin sonido). Sin tema, Alertmanager las descarta (quedan en la pantalla Sistema).
"""
import json
import secrets
import socket
import sys
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "deploy/monitoring/generated"
NTFY = "https://ntfy.sh"

# (nombre visible, destino, módulo de blackbox)
INTERNAL_PROBES = [
    ("App", "http://app:8011/health", "http_2xx"),
    ("LLM", "http://vllm-llm:8000/health", "http_2xx"),
    ("STT", "http://stt-parakeet:8000/health", "http_2xx"),
    ("TTS", "http://vllm-tts:8000/health", "http_2xx"),
    ("Base de datos", "db:5432", "tcp"),
    ("LiveKit", "http://10.250.250.1:7880", "http_2xx"),
    ("Proxy de inferencia", "proxy:80", "tcp"),
]
EXTERNAL_PROBES = [
    ("Internet (Cloudflare)", "1.1.1.1", "icmp"),
    ("Internet (Google)", "8.8.8.8", "icmp"),
    ("DNS", "1.1.1.1", "dns"),
    ("Dashboard por el túnel", "https://app.atentina.com.ar/health", "http_2xx"),
    ("Webhook de WhatsApp", ("https://wa.atentina.com.ar/wa/webhook?hub.mode=subscribe&hub.verify_token=x"
                             "&hub.challenge=1"), "http_403"),
    ("Meta (WhatsApp)", "https://graph.facebook.com", "http_any"),
    ("Resend (mails)", "https://api.resend.com", "http_any"),
    ("Mercado Pago", "https://api.mercadopago.com", "http_any"),
]


def read_env(path: Path) -> dict[str, str]:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def probe_job(name: str, kind: str, probes: list[tuple[str, str, str]], interval: str, host: str) -> list[dict]:
    """Un job por módulo (blackbox pide el módulo como parámetro)."""
    jobs = []
    for module in sorted({p[2] for p in probes}):
        jobs.append({
            "job_name": f"{name}_{module}",
            "scrape_interval": interval,
            "metrics_path": "/probe",
            "params": {"module": [module]},
            "static_configs": [{"targets": [t], "labels": {"probe": n, "kind": kind, "host": host}}
                               for n, t, m in probes if m == module],
            "relabel_configs": [
                {"source_labels": ["__address__"], "target_label": "__param_target"},
                {"source_labels": ["__param_target"], "target_label": "instance"},
                {"target_label": "__address__", "replacement": "blackbox:9115"},
            ],
        })
    return jobs


def prometheus_config(host: str, with_app: bool) -> dict:
    def job(name, target, **kw):
        return {"job_name": name, "static_configs": [{"targets": [target], "labels": {"host": host}}], **kw}

    scrape = [
        job("node", "10.250.250.1:9100"),
        job("llm", "vllm-llm:8000"),
        job("stt", "stt-parakeet:8000"),
        job("tts", "vllm-tts:8000"),
        job("prometheus", "localhost:9090"),
        job("alertmanager", "alertmanager:9093"),
    ]
    if with_app:
        scrape.append(job("app", "app:8011", metrics_path="/internal/metrics", scrape_interval="15s",
                          authorization={"credentials_file": "/etc/prometheus/app_token"}))
    scrape += probe_job("sonda_interna", "interna", INTERNAL_PROBES, "15s", host)
    scrape += probe_job("sonda_externa", "externa", EXTERNAL_PROBES, "30s", host)
    return {
        "global": {"scrape_interval": "5s", "evaluation_interval": "15s"},
        "rule_files": ["/etc/prometheus/rules.yml"],
        "alerting": {"alertmanagers": [{"static_configs": [{"targets": ["alertmanager:9093"]}]}]},
        "scrape_configs": scrape,
    }


# Título: "Atentina: crítica" o "Atentina: aviso"; al resolverse, "Atentina: resuelto".
TITLE = 'Atentina: {{if eq .status "resolved"}}resuelto{{else}}%s{{end}}'
MESSAGE = ('{{range .alerts}}{{if eq .status "resolved"}}OK {{else}}! {{end}}{{.annotations.summary}}\n'
           '{{end}}')


def ntfy_url(topic: str, priority: str, tags: str, severity: str) -> str:
    q = urllib.parse.urlencode({"tpl": "1", "t": TITLE % severity, "m": MESSAGE, "p": priority, "ta": tags})
    return f"{NTFY}/{topic}?{q}"


def alertmanager_config(topic: str) -> dict:
    route = {"receiver": "nada", "group_by": ["alertname"], "group_wait": "30s", "group_interval": "5m",
             "repeat_interval": "4h"}
    receivers = [{"name": "nada"}]
    if topic:
        route["routes"] = [
            {"matchers": ['severity="critical"'], "receiver": "ntfy-alta", "repeat_interval": "1h"},
            {"matchers": ['severity="warning"'], "receiver": "ntfy-baja"},
        ]
        receivers += [
            {"name": "ntfy-alta", "webhook_configs": [{"url": ntfy_url(topic, "high", "rotating_light", "crítica"),
                                                       "send_resolved": True}]},
            {"name": "ntfy-baja", "webhook_configs": [{"url": ntfy_url(topic, "low", "warning", "aviso"),
                                                       "send_resolved": True}]},
        ]
    return {"route": route, "receivers": receivers}


def main(argv: list[str]) -> int:
    env_path = REPO / ".env"
    env = read_env(env_path)
    token = env.get("MONITORING_TOKEN", "")
    if not token:
        token = secrets.token_urlsafe(32)
        with env_path.open("a") as f:
            f.write(f"\n# Prometheus lee /internal/metrics de app con este token (make monitoring-config)\n"
                    f"MONITORING_TOKEN={token}\n")
        print("MONITORING_TOKEN creado y agregado al final de .env (recrear app para que lo tome)")
    host = env.get("MONITORING_HOST") or socket.gethostname()
    OUT.mkdir(parents=True, exist_ok=True)
    # YAML es un superconjunto de JSON: sin dependencias.
    (OUT / "prometheus.yml").write_text(json.dumps(prometheus_config(host, True), indent=2, ensure_ascii=False))
    (OUT / "alertmanager.yml").write_text(json.dumps(alertmanager_config(env.get("ALERT_NTFY_TOPIC", "")),
                                                     indent=2, ensure_ascii=False))
    tok = OUT / "app_token"
    tok.write_text(token)
    tok.chmod(0o644)  # Prometheus corre como nobody; el repo está en el home del usuario
    topic = env.get("ALERT_NTFY_TOPIC", "")
    print(f"Config en {OUT.relative_to(REPO)} (host {host}); alertas: "
          + (f"ntfy, tema {topic[:4]}…" if topic else "SIN ALERT_NTFY_TOPIC, solo en la pantalla Sistema"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

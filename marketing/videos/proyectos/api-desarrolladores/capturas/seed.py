"""Datos ficticios para las capturas del video api-desarrolladores, contra el backend aislado :8114.
El tier copia el Sucursal de produccion (lectura de la tabla tiers, 25-oct-2026)."""
import httpx

B = "http://127.0.0.1:8114/api/v1"
O = {"Origin": "http://127.0.0.1:8114"}
a = httpx.Client(base_url=B, headers=O)
a.post("/auth/login", json={"email": "admin@oime.com.ar", "password": "admin12345"}).raise_for_status()
tier = dict(name="Sucursal", description="Clínicas, comercios y servicios con varias líneas.", max_concurrent_calls=3,
            inbound_minutes=1200, outbound_minutes=1200, max_phone_numbers=3, campaign_channels=["whatsapp", "voice"],
            price_ars=99000, public=True, sort=2, api_llm_input_tokens=262144, api_llm_output_tokens=262144,
            api_tts_minutes=20, api_stt_minutes=20, api_rate_limit=10)
have = {t["name"]: t for t in a.get("/tiers").json()}
if "Sucursal" not in have:
    r = a.post("/tiers", json=tier); print(r.status_code, r.text[:120]); have["Sucursal"] = r.json()
cl = a.post("/clients", json={"name": "Mi Empresa", "slug": "mi_empresa", "tier_id": have["Sucursal"]["id"]})
print(cl.status_code, cl.text[:200]); cid = cl.json()["id"]
u = a.post("/users", json={"email": "dev@miempresa.example", "name": "Ana", "password": "clave-demo-123",
                           "role": "client", "client_id": cid})
print(u.status_code, u.text[:200])

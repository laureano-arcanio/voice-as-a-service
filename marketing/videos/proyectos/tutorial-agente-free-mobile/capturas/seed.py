"""Datos de ejemplo (ficticios) para las capturas del video tutorial-agente-free-mobile, contra el backend
aislado :8113. Los tiers copian los de produccion del 24-oct-2026 (lectura de la tabla tiers)."""
import httpx

B = "http://127.0.0.1:8113/api/v1"
O = {"Origin": "http://127.0.0.1:8113"}
a = httpx.Client(base_url=B, headers=O)
a.post("/auth/login", json={"email": "admin@oime.com.ar", "password": "admin12345"}).raise_for_status()
API = dict(api_llm_input_tokens=262144, api_llm_output_tokens=262144, api_tts_minutes=20, api_stt_minutes=20,
           api_rate_limit=10)
TIERS = [
    dict(name="Free", description="Plan free, pruebas", max_concurrent_calls=1, inbound_minutes=20, outbound_minutes=0,
         max_phone_numbers=0, campaign_channels=[], max_contacts=0, max_call_links=1, max_team_members=0,
         whatsapp=False, price_ars=0, public=True, sort=0, **API),
    dict(name="Mostrador", description="Consultorios, estudios y locales con una línea.", max_concurrent_calls=1,
         inbound_minutes=300, outbound_minutes=300, max_phone_numbers=1, campaign_channels=[], price_ars=29000,
         public=True, sort=1, **API),
    dict(name="Sucursal", description="Clínicas, comercios y servicios con varias líneas.", max_concurrent_calls=3,
         inbound_minutes=1200, outbound_minutes=1200, max_phone_numbers=3, campaign_channels=["whatsapp"],
         price_ars=99000, public=True, sort=2, **API),
    dict(name="Central", description="Empresas medianas y municipios.", max_concurrent_calls=10, inbound_minutes=5000,
         outbound_minutes=5000, max_phone_numbers=6, campaign_channels=["whatsapp"], price_ars=None, public=False,
         sort=0, api_llm_input_tokens=2000000, api_llm_output_tokens=2000000, api_tts_minutes=2000,
         api_stt_minutes=500, api_rate_limit=20),
]
have = {t["name"]: t for t in a.get("/tiers").json()}
for t in TIERS:
    if t["name"] not in have:
        r = a.post("/tiers", json=t); print(t["name"], r.status_code, r.text[:120]); have[t["name"]] = r.json()
cl = a.post("/clients", json={"name": "El Fogón", "slug": "el_fogon", "tier_id": have["Free"]["id"]})
print(cl.status_code, cl.text[:200]); cid = cl.json()["id"]
u = a.post("/users", json={"email": "marta@elfogon.example", "name": "Marta", "password": "clave-demo-123",
                           "role": "client", "client_id": cid})
print(u.status_code, u.text[:200])

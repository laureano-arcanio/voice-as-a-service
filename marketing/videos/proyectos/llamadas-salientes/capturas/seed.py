"""Datos ficticios para las capturas del video llamadas-salientes, contra el backend aislado :8115.
El tier copia el Sucursal de produccion (con llamadas directas). Deja un numero libre en el inventario (se asigna
en la captura), una persona del equipo y contactos; el resto (la persona Ana y el contacto nuevo) se crea en pantalla."""
import httpx

B = "http://127.0.0.1:8115/api/v1"
O = {"Origin": "http://127.0.0.1:8115"}
a = httpx.Client(base_url=B, headers=O)
a.post("/auth/login", json={"email": "admin@oime.com.ar", "password": "admin12345"}).raise_for_status()
tier = dict(name="Sucursal", description="Clínicas, comercios y servicios con varias líneas.", max_concurrent_calls=3,
            inbound_minutes=1200, outbound_minutes=1200, max_phone_numbers=3, campaign_channels=["whatsapp", "voice"],
            price_ars=99000, public=True, sort=2, max_team_members=10, max_contacts=2000, direct_calls=True,
            advanced_reports=True, whatsapp=True, max_campaigns_per_month=10, max_campaign_contacts=500,
            max_campaign_concurrency=3, max_call_links=5)
have = {t["name"]: t for t in a.get("/tiers").json()}
if "Sucursal" not in have:
    r = a.post("/tiers", json=tier); print(r.status_code, r.text[:160]); have["Sucursal"] = r.json()
cl = a.post("/clients", json={"name": "Mi Empresa", "slug": "mi_empresa", "tier_id": have["Sucursal"]["id"]})
print(cl.status_code, cl.text[:160]); cid = cl.json()["id"]
u = a.post("/users", json={"email": "dev@miempresa.example", "name": "Ana Ríos", "password": "clave-demo-123",
                           "role": "client", "client_id": cid})
print(u.status_code, u.text[:160])
# Inventario: un numero libre (se asigna en pantalla) y otro de otro lote
for e164, label in [("+541152630861", "Ventas"), ("+541152630862", "Lote octubre")]:
    r = a.post("/phone-numbers", json={"e164": e164, "label": label}); print(r.status_code, r.text[:120])

# Del lado del cliente
c = httpx.Client(base_url=B, headers=O)
c.post("/auth/login", json={"email": "dev@miempresa.example", "password": "clave-demo-123"}).raise_for_status()
me = c.get("/auth/me").json()
pend = me.get("legal_pending") or []
print("pendientes", [(p["document"] if "document" in p else p) for p in pend][:2])
if pend:
    tv = next(p["version"] for p in pend if p.get("id") == "terms" or p.get("document") == "terms")
    pv = next(p["version"] for p in pend if p.get("id") == "privacy" or p.get("document") == "privacy")
    r = c.post("/auth/me/legal", json={"terms_version": tv, "privacy_version": pv}); print("legal", r.status_code)
r = c.post("/team", json={"name": "Pedro Gómez", "phone": "351 555-0134"}); print("team", r.status_code, r.text[:120])
for nombre, tel, nota in [("Juan Pérez", "+5493515550101", "Cliente desde 2024. Prefiere que lo llamen por la mañana."),
                          ("María Gómez", "+5493515550117", ""), ("Ferretería Sur", "+5493515550123", "Pedido de cañerías pendiente."),
                          ("Lucas Benítez", "+5493515550138", ""), ("Silvia Torres", "+5493515550149", "")]:
    r = c.post("/contacts", json={"phone": tel, "name": nombre, "notes": nota}); print("contacto", r.status_code, r.text[:100])

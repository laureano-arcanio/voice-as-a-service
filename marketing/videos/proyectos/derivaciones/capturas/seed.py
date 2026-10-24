"""Datos de ejemplo (ficticios) para las capturas del video derivaciones, contra el backend aislado :8112."""
import httpx

B = "http://127.0.0.1:8112/api/v1"
O = {"Origin": "http://127.0.0.1:8112"}
a = httpx.Client(base_url=B, headers=O)
r = a.post("/auth/login", json={"email": "admin@oime.com.ar", "password": "admin12345"}); r.raise_for_status()
tiers = a.get("/tiers").json()
print([(t["name"], t["id"]) for t in tiers])
tier = next(t for t in tiers if t["name"].lower().startswith("interno")) if any(t["name"].lower().startswith("interno") for t in tiers) else tiers[0]
cl = a.post("/clients", json={"name": "Aires del Sur", "slug": "aires_del_sur", "tier_id": tier["id"]})
print(cl.status_code, cl.text[:200]); cid = cl.json()["id"]
u = a.post("/users", json={"email": "carla@airesdelsur.example", "name": "Carla", "password": "clave-demo-123",
                           "role": "client", "client_id": cid})
print(u.status_code, u.text[:200])

c = httpx.Client(base_url=B, headers=O)
c.post("/auth/login", json={"email": "carla@airesdelsur.example", "password": "clave-demo-123"}).raise_for_status()
people = [("Lucía Romero", "351 555-0142"), ("Diego Ferreyra", "351 555-0178"),
          ("Martina Sosa", "351 555-0193"), ("Julián Ortiz", "351 555-0127")]
ids = {}
for n, p in people:
    r = c.post("/team", json={"name": n, "phone": p}); print(r.status_code, r.text[:160]); ids[n] = r.json()["id"]
wk = lambda fr, to, days: {d: [[fr, to]] for d in days}
LV = ["mon", "tue", "wed", "thu", "fri"]
areas = [
    ("Ventas", "Precios, presupuestos de instalación y visitas al showroom.", ["Lucía Romero", "Diego Ferreyra"],
     {**wk("09:00", "18:00", LV), "sat": [["09:00", "13:00"]]}),
    ("Soporte técnico", "Equipos que no enfrían, ruidos, service y garantías.", ["Martina Sosa", "Diego Ferreyra"],
     wk("08:00", "20:00", LV)),
    ("Administración", "Facturas, pagos y cuotas.", ["Julián Ortiz"], wk("09:00", "17:00", LV)),
]
aids = {}
for n, d, m, week in areas:
    r = c.post("/handoff-areas", json={"name": n, "description": d, "member_ids": [ids[x] for x in m],
                                       "schedule": {"week": week}})
    print(r.status_code, r.text[:200]); aids[n] = r.json()["id"]
ag = c.post("/agents", json={"name": "Atención al cliente", "template_id": "asistente", "engine": "classic"})
print(ag.status_code, ag.text[:300])
print("client", cid)

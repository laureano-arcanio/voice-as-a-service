"""Saca a Lucía y el área Ventas para capturar su alta desde la UI."""
import httpx
B = "http://127.0.0.1:8112/api/v1"
c = httpx.Client(base_url=B, headers={"Origin": "http://127.0.0.1:8112"})
c.post("/auth/login", json={"email": "carla@airesdelsur.example", "password": "clave-demo-123"}).raise_for_status()
import time
for ag in c.get("/agents").json():
    d = c.get(f"/agents/{ag['id']}").json()["definition"]
    if d.get("handoff", {}).get("areas"):
        d["handoff"]["areas"] = []
        print("agente", c.put(f"/agents/{ag['id']}/definition", json={"definition": d}).status_code)
    print("archivar", c.patch(f"/agents/{ag['id']}", json={"archived": True}).status_code)
print("nuevo", c.post("/agents", json={"name": "Atención al cliente", "slug": f"atencion_{int(time.time())}",
                                      "template_id": "asistente"}).status_code)
for a in c.get("/handoff-areas").json():
    if a["name"] == "Ventas": print(c.delete(f"/handoff-areas/{a['id']}").status_code)
for m in c.get("/team").json():
    if m["name"] == "Lucía Romero": print(c.delete(f"/team/{m['id']}").status_code)

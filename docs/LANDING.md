# Landing (atentina.com.ar)

HTML plano en [`landing/`](../landing/), sin build: `index.html` (CSS y JS adentro),
`favicon.svg`, `og.png`, `robots.txt` y `sitemap.xml`. Se sirve como sitio estático
gratis de Render, definido en [`render.yaml`](../render.yaml).

- **Canónico:** `https://atentina.com.ar/`. `www.atentina.com.ar`, `atentina.com` y
  `www.atentina.com` redirigen ahí con 301.
- **Probar en local:** `python3 -m http.server -d landing 8080`.
- **Publicar:** push a la rama que sigue Render; solo los cambios en `landing/` despliegan.
- **`og.png` y logos:** se generan en `scratch/logo/` (`build_atentina.py`, `og.html`).

## Alta (una vez)

1. **Render:** New → Blueprint → este repo. Crea el sitio `atentina-landing` con el
   dominio `atentina.com.ar` (y `www`). Anotar el host `*.onrender.com` que le asigna.
2. **`atentina.com.ar` en Cloudflare:** agregar el sitio (plan gratis) y, en NIC
   Argentina, delegar el dominio a los dos nameservers que da Cloudflare. NIC solo
   delega: los registros van en Cloudflare.

   | Tipo | Nombre | Destino | Proxy |
   |---|---|---|---|
   | CNAME | `@` | `atentina-landing.onrender.com` | solo DNS |
   | CNAME | `www` | `atentina-landing.onrender.com` | solo DNS |

   Con "solo DNS", Render emite el certificado y sirve desde su CDN. Después,
   "Verify" en los dominios del sitio en Render.
3. **`atentina.com` en Cloudflare:** no llega a Render, redirige desde Cloudflare.

   | Tipo | Nombre | Destino | Proxy |
   |---|---|---|---|
   | AAAA | `@` | `100::` | con proxy |
   | AAAA | `www` | `100::` | con proxy |

   Rules → Redirect Rules: si el hostname es `atentina.com` o `www.atentina.com`,
   redirigir 301 a `concat("https://atentina.com.ar", http.request.uri.path)`,
   conservando el query string.
4. **Correo:** la landing publica `hola@atentina.com.ar`. Cloudflare Email Routing
   (gratis) en `atentina.com.ar` lo reenvía a una casilla existente.
5. **Google Search Console:** propiedad de dominio `atentina.com.ar` (TXT en
   Cloudflare) y enviar `https://atentina.com.ar/sitemap.xml`.

## Pendiente: la app

Todavía no está publicada. Lo decidido: `app.atentina.com.ar` sirve la app y
`app.atentina.com` redirige ahí (misma Redirect Rule de Cloudflare, con ese
hostname). Falta elegir dónde corre (este server con Cloudflare Tunnel, o Render)
y, cuando exista, sumar el link "Ingresar" en la landing.

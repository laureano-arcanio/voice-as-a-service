# Theme Yoizen (marca blanca)

Primer theme del plan [`ARQUITECTURA.md`](../../../docs/ARQUITECTURA.md). Armado el 26-oct-2026 a partir
de [yoizen.com](https://yoizen.com/) (Yoizen S.A., CABA: plataforma omnicanal y agentes de IA; lead #106 del CRM).
Variante elegida: **encabezado oscuro con la versión clara del logotipo** (la A de la vista previa).

- `theme.json`: `branding` es el cuerpo del `PUT /api/v1/clients/{id}/branding`; `resolved` es lo que calcula la app (texto del header, contrastes, proporción del logo y la escala de 10 tonos que pisa a `blue`).
- `logo-claro.svg`: el que se sube. Es el logotipo primario de su sitio con la tinta `#272a35` pasada a blanco (el símbolo azul, violeta y naranja queda igual). Va sobre el encabezado `#272a35` en el header y, en el login, sobre una pastilla de ese mismo color. 3,5 KB, viewBox 904 × 243 (proporción 3,71: a 28 px de alto ocupa 104 px). Pasa el filtro de SVG de la app (tiene `<defs><style>` con 4 clases y nada más).
- `logo.svg`: el original (tinta oscura), para fondos blancos. No se usa en el panel; queda como fuente.
- `preview.html`: el panel con esa marca, estático y sin dependencias (abrir en el navegador). Las capturas reales del panel de desarrollo con esta marca están en `scratch/marca-blanca/ui-*.png` (no versionadas).
- Los logos son activos de Yoizen: se usan para su panel y para esta prueba, no en material propio.

## De dónde salen los colores

| Rol | Valor | Origen | Contraste |
|---|---|---|---|
| Primario | `#0068fd` | Azul del logo (`fill` en `logo.svg`); el sitio usa `#1a66ff` en botones y links, casi el mismo (4,79:1) | 4,77:1 sobre blanco: pasa el mínimo de 4,5 |
| Encabezado | `#272a35` | Tinta del logotipo; el sitio tiene los botones y el menú "Hablemos" en negro | Texto blanco, 14,3:1 |
| Acento | `#4d39c3` | Violeta del logo y del degradado de su portada (azul → violeta) | Solo en la segunda serie de los gráficos |

- **Descartado:** el naranja `#fd6421` del logo. Sobre blanco da 2,99:1 (la API lo rechaza con `color_contrast` y sugiere `#c04b19`) y en el panel se confundiría con el amarillo de "atención".
- Tipografía: su sitio usa Barlow y Poppins. No se cambia: el panel sirve sus fuentes (CSP `font-src 'self'`), y el plan no personaliza tipografías.

## Cómo cargarlo

Ficha del cliente → pestaña "Marca blanca" → subir `logo-claro.svg`, pegar los tres colores, prender "Mostrar el panel con la marca del cliente" y "Guardar". El plan del cliente tiene que incluir la marca blanca (Interno, o prenderla en su tier: Red es a medida). Probar el login con `https://app.atentina.com.ar/login?c=yoizen`. Por API: `scratch/marca-blanca/seed_yoizen.sh` lo hace contra el backend de desarrollo.

# Formato de cada tanda

Cada tanda son dos archivos con el mismo nombre: `<fecha>-<slug>.md` (los textos para copiar) y
`<fecha>-<slug>.csv` (la ficha). El estado de cada contacto vive en [`../seguimiento.md`](../seguimiento.md).

## Emails: todos los encontrados, y el de mayor potencial marcado

Por empresa se buscan y se registran **todos** los emails publicados que sirvan:

- **persona:** el de un directivo o responsable con nombre (dueño, socio, gerente general, comercial,
  de atención, de cobranzas, de sistemas; en cooperativas, el presidente; en municipios, el secretario).
- **área:** casillas de un área que no son la genérica (`gerencia@`, `comercial@`, `cobranzas@`, `sistemas@`).
- **atención:** la de atención normal (`info@`, `contacto@`, `atencionalcliente@`). Va siempre, como alternativa.

Cada email figura literal en una fuente que se abrió (sitio, ficha de cámara, prospecto, boletín
oficial, prensa), con URL y fecha. Nada deducido por patrón ni sacado de snippets enmascarados.
Los emails de recursos humanos, búsquedas laborales o sucursales sueltas no se anotan.

**Mayor potencial (★):** el destinatario del mail. En este orden:

1. Persona que decide sobre lo que tocamos (atención, cobranza, comercial, sistemas) o el número
   uno, con fuente de 2024 en adelante.
2. Otra persona directiva con fuente reciente, o la del punto 1 con fuente vieja (puede rebotar: se anota).
3. Casilla de área relacionada con atención, cobranza o comercial.
4. La de atención.

Si el mail ya salió a otra dirección, el ★ es a quién sumar en el seguimiento (mismo hilo).

## `.md`

Encabezado con el estado (borrador o enviado), notas de la tanda y una tabla
`# | Empresa | Web | Email ★ | Tipo | Quién`. Después, por empresa:

````
## 32. Elebar

- Rubro: Tarjeta de crédito regional, Tandil (Buenos Aires)
- Web: https://www.elebar.com.ar
- Tipo: posible cliente
- Gancho: <de dónde sale, para revisar>

Emails encontrados (verificados el 5-oct-2026):

| | Email | Tipo | Quién | Fuente (fecha) |
|---|---|---|---|---|
| ★ | pbernatene@elebar.com.ar | persona | María Paz Bernatene, gerente de Créditos y Cobranzas | <url> (13-ago-2026) |
| | camilo.granel@elebar.com.ar | persona | Camilo Granel, director de Sistemas y Operaciones | <url> (13-ago-2026) |
| | info@elebar.com.ar | atención | — | <url> |

★ porque <una línea>. Sin email: <nombre, cargo; nombre, cargo> (opcional).

Para:

```
pbernatene@elebar.com.ar
```

Asunto:
...
Texto:
...
````

- El saludo nombra a la persona solo si el ★ es su casilla; a una casilla de área o de atención, "Hola, ¿cómo están?".
- Contacto ya enviado: "Para" queda con la dirección a la que salió, y una línea `Enviado a <email> el <fecha>; ★ para el seguimiento`.

## `.csv`

Una fila por empresa con:
`n, empresa, rubro, ciudad_provincia, web, email, email_tipo, contacto_nombre_cargo, url_donde_figura_el_email, fuente_fecha, email_generico, emails_encontrados, por_que_encaja, gancho`.

- `email`, `email_tipo`, `contacto_nombre_cargo`, `url_donde_figura_el_email` y `fuente_fecha` son los del ★.
- `email_generico`: la de atención.
- `emails_encontrados`: todos, separados por `; `, cada uno como `email (tipo, quién, fecha)`.

Las tandas 2 y 3 llevan además el link con UTM (columna `utm_content` en la tabla del `.md` y
`utm_campaign`, `utm_content` en el `.csv`); el registro está en `seguimiento.md`, "Links con UTM".

## Envío desde Gmail

`python3 scripts/mercado/envio_html.py docs/mercado/envios/<tanda>.md` genera `scratch/envios/<tanda>.html`:
por empresa, botones para copiar destinatario, asunto y texto. El texto se pega en Gmail con formato y el
link con UTM queda como "atentina.com.ar" enlazado. En el `.md` el link sigue completo, como registro.

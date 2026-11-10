# Propuesta para Empresa La Estrella

- **Pedido (7-nov-2026, sesión principal por encargo de Laureano):** propuesta comercial en PDF para Empresa La Estrella
  (colectivos de corta y media distancia, Resistencia, Chaco). Máximo 2 hojas A4, sencilla, sin terminología técnica,
  sin precios. Orden: introducción positiva; la propuesta (agente que atiende todas las llamadas, consulta sus sistemas,
  no vende y deriva a la sucursal); hincapié en la observabilidad; etapa 1 de diagnóstico (en 10 días, 1 a 2 semanas,
  llamadas directo a la persona sin agente, línea de base); etapa 2 escalonada por sucursal; cómo funciona con diagrama
  (fijo o 0800 → agente → teléfono IP en la sucursal); qué esperan obtener; próximos pasos. Sin teléfonos, emails, CUIT,
  nombres de personas ni los problemas encontrados en su sitio o reseñas.
- **Destinatario:** la dirección de Empresa La Estrella, después de la charla del 6-nov-2026.
- **Objetivo:** que confirmen las 6 sucursales, el acceso a horarios y el desvío para arrancar la etapa 1 en 10 días.
- **Formato:** A4, 2 hojas. `make doc P=laestrella-propuesta V=<n> HOJAS=2`.
- **Fuente de la empresa:** [`comercial/demos/laestrella.md`](../../../../comercial/demos/laestrella.md) (leída el 7-nov-2026).

## Estructura (v1)

1. **Hoja 1:** título "Todas las llamadas atendidas, y por primera vez, medidas."; cuatro cifras de la empresa; línea
   de vanguardia; la propuesta (lo que resuelve el agente / lo que pasa a la sucursal); bloque de observabilidad (8
   métricas y para qué sirven).
2. **Hoja 2:** las dos etapas; diagrama "Cómo funciona" con los dos mensajes clave; cinco beneficios; tres próximos
   pasos; nota; pie de contacto.

## Afirmaciones y de dónde salen

- **"+90 años":** el gerente dijo 89 años en ene-2024 (Diario Norte, 10-ene-2024); en nov-2026 son unos 91. El pedido
  decía "casi 90": se puso "+90" por ser lo correcto. A confirmar con ellos.
- **13 corredores, unas 60 localidades:** sitio de la empresa (`horarios.js`), en `laestrella.md` parte 0 y 2.5.
- **6 sucursales:** lo que pidieron en la charla del 6-nov-2026; la lista no está confirmada (es el próximo paso 1).
- **Encomiendas, alquiler, tarjeta prepaga con recarga digital, venta en línea:** sitio y portal de pasajes.
- **Agente 24 h, deriva con horario y toma de mensaje:** `docs/features/EQUIPO_TELEFONIA.md` (en producción).
- **Etapa 1, llamadas directo a la persona sin agente, grabadas y transcriptas:** "entrante al equipo"
  (`answer_mode=team`), en producción desde el 27-oct-2026 pero **sin probar con llamadas reales** (EQUIPO_TELEFONIA).
- **Métricas (por sucursal, horario, perdidas, derivaciones, quién atendió, transcripción):** `docs/features/REPORTES.md`
  (`/reports/calls` con `by_line`, `heatmap`, `by_type`, `ended`; transferencias con `advanced_reports`). El "motivo"
  sale de los resultados del agente y, en la etapa 1, del análisis de las transcripciones.
- **Consulta de horarios y disponibilidad "conectado a sus sistemas":** herramientas `http` (HERRAMIENTAS.md, en
  producción) o la tabla cargada en el agente; la forma depende de lo que tengan (próximo paso 2).
- **0800:** la landing ofrece numeración 0800 y 0810 (`site.ts`, FAQ).
- **Teléfono IP en cada sucursal:** pedido del usuario. **A validar:** la plataforma documenta derivar a celulares y al
  panel o la app `telefono.`; un teléfono IP de escritorio no está en los docs (equipo, registro y quién lo instala).
  Desde v2 dice "se instala", sin decir quién. Resuelve además el riesgo de derivar a un fijo que está desviado al agente.
- **Plazo de 10 días y etapas:** promesa comercial del pedido. **A validar.**
- **Omitido:** precios, capacidad de llamadas simultáneas (sin CAP vigente; solo "varias a la vez"), problemas del sitio
  y reseñas, teléfonos, CUIT y nombres.

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 7-nov-2026 | Primera versión | cerrada |
| [v2](versiones/v2/NOTAS.md) | 7-nov-2026 | Teléfono IP: "se instala", no lo instalamos nosotros | cerrada |
| [v3](versiones/v3/NOTAS.md) | 7-nov-2026 | Desvío activado desde el teléfono con un código; fuera la dependencia de la compañía telefónica | cerrada |
| [v4](versiones/v4/NOTAS.md) | 7-nov-2026 | Mail del pie: laureano@atentina.com.ar | borrador |

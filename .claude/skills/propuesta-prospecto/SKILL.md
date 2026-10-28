---
name: propuesta-prospecto
description: Investiga una empresa prospecto y arma su PDF de propuesta y su video de análisis, como se hizo con Isaías Goldman y BAIC Center. Coordina a los agentes ventas (base de conocimiento), documentos (PDF) y videos (video que sigue al PDF) pasándoles la información de la empresa. Usar cuando el usuario pide "investigá <empresa> y armá el video y el documento", "hacé la propuesta y el video para <empresa>", o el PDF y el video para un prospecto que ya tiene base en comercial/demos/.
---

# Propuesta de un prospecto: investigación, PDF y video

Lo corre la sesión principal (los subagentes no pueden lanzar otros): delega en tres agentes, en orden, y cada uno
recibe lo que dejó el anterior. Las plantillas son los proyectos de Goldman y BAIC:

| Paso | Agente | Sigue | Deja | Ejemplos |
|---|---|---|---|---|
| 1. Investigar | `ventas` | `comercial/demos/PLANTILLA.md` | `comercial/demos/<slug>.md` | `isaiasgoldman.md`, `baicenter.md` |
| 2. PDF | `documentos` | `marketing/DOCUMENTOS.md` | `marketing/documentos/proyectos/<slug>-propuesta/` | `goldman-propuesta`, `baicenter-propuesta` |
| 3. Video | `videos` | `marketing/VIDEOS.md` | `marketing/videos/proyectos/<slug>-analisis/` | `goldman-analisis` (v3), `baicenter-analisis` |

El video va después del PDF porque copia su estructura, textos y cifras.

## 0. Datos del pedido

Del mensaje del usuario sacá: empresa y sitio, contacto (nombre y cargo), cómo llegamos (llamada, reunión, lead frío),
objetivo (por defecto: reunión de relevamiento y piloto de 30 días) y lo específico que pida. Si falta el nombre o el
sitio, preguntá; lo demás tiene default. Elegí un `<slug>` corto (`isaiasgoldman`, `baicenter`).

**Énfasis** (preguntá solo si no está claro; default, el de BAIC):
- `oportunidades` (default): "Dónde podríamos mejorar con Atentina", tarjetas con su oportunidad, sin nombrar fallas del
  sitio ni a la competencia, pocas reseñas y junto a lo positivo.
- `observado`: "Lo que observamos" y "Lo que dicen sus clientes", hechos y citas textuales en tono amable (Goldman).

Mirá `git status` y si ya existen la base o los proyectos: si existen, se hace una versión nueva, no se pisa.

## 1. Investigar (agente `ventas`)

Saltear si `comercial/demos/<slug>.md` ya existe y el usuario no pidió actualizarla. Si no:

```
Investigá a fondo <empresa> (<sitio>) siguiendo comercial/demos/PLANTILLA.md (tarea "Investigar una empresa").
Contacto: <nombre, cargo>. Contexto: <cómo llegamos>. Objetivo: <objetivo>. Lo que ya sabemos: <datos del usuario>.
Slug: <slug>. Fecha de hoy: <fecha>. La base va a alimentar un PDF de propuesta y un video, así que en la parte 0 y la 5
dejá cifras concretas con fuente (años, tamaño, reseñas y rating, canales de contacto, horario en horas abiertas por
semana, productos con o sin precio, citas del dueño en prensa o video) y en la 7 el caso de uso, el diagrama de canales
→ agente → áreas del equipo, y las métricas que querría ver el dueño en un panel.
Devolveme el resumen de la plantilla.
```

Al volver: pasale al usuario el resumen en pocas líneas (quién es, dolores, caso de uso) y seguí, salvo que haya algo
que decidir (la empresa no es lo que se esperaba, no hay datos suficientes, el caso de uso no es obvio).

## 2. PDF (agente `documentos`)

```
Armá un PDF de propuesta (proyecto nuevo <slug>-propuesta, v1) para <empresa> (<rubro, ciudad>). Destinatario:
<contacto y cargo; otros decisores de la base>. Lo manda Atentina después de <contexto>. Seguí marketing/DOCUMENTOS.md.
Base de conocimiento: comercial/demos/<slug>.md (partes 0, 1, 2, 4, 5 y 7). Formato, estructura y estética: copiá
marketing/documentos/proyectos/goldman-propuesta/ y baicenter-propuesta/ (README, NOTAS y documento.html).

Pedido del usuario, textual: "<texto del usuario o: Un PDF con el análisis de su situación actual, fáctico pero con
lenguaje amable. La solución propuesta. Y cómo se pondría en marcha.>"

Estructura (A4, 4 a 6 hojas):
1. Portada y quiénes son: un h1 que resuma la promesa para ellos; lo que ya hacen bien (cuatro cifras con fuente) y
   una cita del dueño si la hay.
2. <énfasis observado: "Lo que observamos" (hechos con fuente) y "Lo que dicen sus clientes" (citas cortas textuales,
   sin nombres, presentadas como lo que dicen sus clientes)> | <énfasis oportunidades: "Dónde podríamos mejorar con
   Atentina": cada hecho con su oportunidad, sin nombrar fallas del sitio ni a la competencia; dos reseñas a lo sumo,
   junto a lo positivo>. Contexto del rubro o la temporada si suma.
3. La solución: el agente en sus canales (los de la parte 7 de la base: línea, WhatsApp, web), qué resuelve solo y a
   qué área del equipo deriva; diagrama SVG canales → agente que clasifica → su equipo, todo → panel.
4. El panel como pilar para el dueño: mock con datos ilustrativos rotulados así (por canal, por tipo, fuera de horario,
   resueltas vs. derivadas, quién tomó cada consulta y cuánto tardó) y la tabla "lo observado → qué lo resuelve".
5. Puesta en marcha: piloto de 30 días con alcance acotado, pasos (relevamiento, configuración y pruebas, línea de base,
   salida en vivo, revisión semanal, decisión con números), qué necesitamos de ellos, fases posteriores, contacto.

Reglas: material de venta, todo se presenta como la oferta sin decir qué está construido (eso va en "A validar" del
README, contra la parte 7.4 de la base). Sin precios nuestros: el del piloto se acuerda en la reunión. Documento de
Atentina: el nombre de <empresa> escrito, sin su logo ni su marca. Cada afirmación con su fuente en el README.
<Pedidos específicos del usuario.>
Generá el PDF, revisalo con los controles de marketing/DOCUMENTOS.md y devolveme la ruta, las hojas, la estructura y dudas.
```

## 3. Video (agente `videos`)

```
Hacé un video nuevo (proyecto <slug>-analisis, v1) para <empresa> siguiendo el formato y contenido del PDF ya hecho:
marketing/documentos/proyectos/<slug>-propuesta/versiones/v<n>/documento.html (leelo completo: es la fuente de textos,
cifras y tono) y comercial/demos/<slug>.md. Seguí marketing/VIDEOS.md. Plantilla: copiá la estructura de
marketing/videos/proyectos/goldman-analisis/ (v3) y baicenter-analisis/ (README, guion.json, src/, NOTAS).

Pedido del usuario: "<texto del usuario o: el PDF en video, con la introducción, qué hacen bien y <qué observamos |
dónde podríamos mejorar con Atentina>. Corto, 60 segundos.>"

Escenas (~60 s, hasta ~65): intro oscura como la portada del PDF (2 s de espera antes de la voz) · lo que ya hacen bien
(tarjetas de cifras) · la cita del dueño si la hay · <lo observado | dónde podríamos mejorar>, una tarjeta por frase con
un respiro de ~0,7 s entre cada una · lo que dicen sus clientes (si el PDF lo tiene) · la propuesta: canales → logo de
Atentina (AgenteLogo) → tipos de consulta → su equipo por área, con énfasis en Ventas · el panel simple: pocas cifras +
quién tomó cada consulta y cuánto tardó, rotulado "EJEMPLO CON DATOS ILUSTRATIVOS" · cierre oscuro solo con
"¿Agendamos una reunión personalmente?" y el contacto de Atentina chico abajo.

Reglas: narradora paula a 1× y pablo como voz secundaria en algunas líneas (marketing/VIDEOS.md, Voces), ortografía normal (grafías especiales solo si una palabra sale mal en las tomas), pausas
con puntuación, "En <empresa>..." para nombrarla y probar cómo pronuncia el nombre; el agente es el logo de Atentina
(sin robot); sin logo ni marca de <empresa>; material de venta, sin decir qué está construido. En archivos compartidos
(src/Root.tsx, src/comun/*, marketing/README.md) solo agregá líneas y releé antes de editar.
<Pedidos específicos del usuario.>
Renderizá, revisá con los controles de marketing/VIDEOS.md (tomas, transcripción, finales de frase, cuadros) y devolveme la
ruta del MP4, la duración, la locución por escena y dudas.
```

## 4. Al usuario

- Rutas: base `comercial/demos/<slug>.md`, PDF y MP4.
- Resumen de la empresa en 5 líneas y la propuesta en una.
- **A validar antes de mandar**, juntando lo de los dos README: funciones ofrecidas que no están desplegadas, datos sin
  verificar, promesas comerciales (piloto, fechas) y pronunciaciones a escuchar.
- Los cambios del usuario sobre el PDF o el video van como versión nueva con el mismo agente (SendMessage si sigue
  vivo); si cambia un texto o una cifra en el PDF, pasárselo también al de videos para que queden iguales.
- Sin commit salvo que lo pida. No se manda nada al prospecto: lo manda el usuario.

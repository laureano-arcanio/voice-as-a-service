# Browix — Contexto del agente comercial

**Agente:** Sofía, asesora comercial virtual de Browix (`AGENT_NAME` / `COMPANY_NAME` en `.env`).
**Caso de uso:** una persona interesada **llama** a Browix (llamada entrante vía Anura → Asterisk →
LiveKit, ver `docs/TELEFONIA_ANURA.md`). El agente ofrece contarle los servicios, hace una
presentación breve, califica el lead con el cuestionario configurado y cierra con una demo sin
compromiso con un asesor humano. Las salientes desde el dashboard y el modo prueba usan el mismo agente.

**Saludo** (igual en todos los casos, `first_message` en `app/prompts.py`):
*"Hola Francisco, te habla Sofía de Browix. Si querés te cuento qué servicios tenemos para ofrecerte."*
En las entrantes el nombre es siempre `INBOUND_CALLER_NAME` (default `Francisco`; si el que llama
lo corrige, el agente sigue con el nombre real). En salientes y modo prueba sale del campo "Nombre
del interesado" del dashboard; si está vacío saluda sin nombre y se lo pregunta.

**Presentación breve** (si acepta): "Browix es una plataforma para gestionar al personal de tu
empresa, esté en la oficina, en sucursales o en la calle. Tiene control horario con foto y GPS,
recibos de sueldo digitales que se firman desde el celular, seguimiento de tareas en terreno y
comunicación interna con un asistente de inteligencia artificial." → sigue con la primera pregunta.

Relevado de https://browix.com el 21/09/2026. La versión condensada que usa el agente vive en
`app/prompts.py` (`KNOWLEDGE_BASE`); si el sitio cambia, actualizar ambos.

## Dónde vive cada cosa

| Qué | Dónde |
| --- | --- |
| Prompt del agente + base de conocimiento | `app/prompts.py` |
| Preguntas de calificación y bandas (seed) | `app/db.py` → `SEED_QUESTIONS`, `SEED_BANDS` (editables en `/config`) |
| Evaluador del lead (post-llamada) | `app/scoring.py` |
| Temperatura del lead | `caliente` (70–100) · `tibio` (40–69) · `frio` (0–39); si falla una pregunta requerida, `caliente` baja a `tibio` |

## La empresa

- **Qué es:** plataforma de gestión de personal. "Digitalizá tu empresa con Browix. App para control
  horario, recibos de sueldo y gestión de RRHH: todo en una plataforma simple."
- **Para quién:** empresas con personal distribuido — en la oficina, en sucursales o en la calle.
- **Ubicación:** Córdoba, Argentina. Contacto: info@browix.com.
- **Diferenciales de la home:** 100% online y en tiempo real · compatible con la Ley de Firma Digital ·
  funciona online y offline · licencias en pesos, sin sorpresas.
- **Resultados publicados:** 5% de ahorro en horas facturadas · 27% menos de tiempos perdidos · 75% de
  ahorro en procesamiento de datos.
- **Clientes (logos en la home):** Zemts, Trademan, Lavoris, CapitalBox, Camiare, Berlim, Zentinel,
  Via Verde, Mega Clean, Grupo Sarmiento, Euroclean, Dulcor, Ecoservice, Aconcagua.

### Recorrido sugerido por Browix

1. **Ordená el control horario:** fichaje con foto y GPS, turnos rotativos y variables, alertas de dotación.
2. **Digitalizá recibos y legajo:** recibos con firma PIN y legajo con vencimientos, con validez legal.
3. **Llevá la operación al sistema:** tareas y órdenes de trabajo, relevamientos, uniformes y EPP.
4. **Completá la gestión de RRHH:** selección, capacitaciones y el Asistente IA.

## Módulos

### Tiempo y Presentismo — [tiempo-y-presentismo.html](https://browix.com/tiempo-y-presentismo.html)

- **Control de presentismo:** foto en cada marcación con detección de rostro + fecha, hora y GPS validado
  contra la sucursal. Punto fijo (tablet compartida) o celular propio si es itinerante. Funciona sin
  internet y sincroniza al reconectar. Detecta ubicación simulada, GPS apagado y hora adulterada.
  Olvidos y discrepancias con bandeja de resolución para el supervisor.
- **Reconocimiento facial y prueba de vida:** discrepancia de rostro contra el titular; prueba de vida
  ante inicios de sesión sospechosos; verificación de identidad por persona o en lote.
- **Jornadas y turnos:** fijos, rotativos, variables y automáticos, con feriados. Turnos complejos
  (24 hs, 4x1, 14x14, 5x2) cargados en forma masiva. Planificación por empleado o por ubicación,
  importación desde Excel. Reglas y alertas: dotación crítica por servicio, abandono de puesto,
  marcación fuera de zona. Contratos para comparar horas pactadas vs. trabajadas.
- **Vacaciones, licencias y solicitudes:** tipos configurables con adjuntos, circuito de aprobación
  (también desde la app del supervisor), saldos de vacaciones por período, KPIs de ausentismo.
  Reemplaza los grupos de WhatsApp.
- **Liquidación de horas:** cálculos automáticos y fórmulas por empresa, dashboard en tiempo real,
  reportes por centro operativo/grupo/empresa/sucursal con exportación a Excel.

### Gestión de Personas — [gestion-de-personas.html](https://browix.com/gestion-de-personas.html)

- **Recibos de sueldo digitales:** se sube un PDF con todos los recibos; Browix los corta, asigna y
  notifica (email + push). Firma con PIN, con conformidad/disconformidad y comentarios. Panel con
  estado leído/firmado/conforme. Marco legal: Res. 346/2019 (recibos digitales) y Ley 25.506 (firma).
- **Legajo digital:** carpetas por tipo de documento, firma con PIN u ológrafa en pantalla, avisos de
  vencimiento, carpetas confidenciales, reporte de documentación pendiente.
- **Plantillas de documentos:** sanciones, notificaciones, constancias; campos autocompletados desde el
  perfil o un Excel; editor visual o sobre un PDF existente.
- **Capacitaciones:** videos, links y archivos; evaluaciones con puntaje de aprobación; certificado al legajo.
- **Uniformes y EPP:** catálogo, talles por empleado, stock, entregas con comprobante firmado, pedidos
  desde la app.
- **Selección y reclutamiento:** base de candidatos, procesos por etapas, mensajes masivos, onboarding
  en un clic (pasa a la nómina con sus datos y capacitaciones iniciales).

### Operaciones en Terreno — [operaciones-en-terreno.html](https://browix.com/operaciones-en-terreno.html)

- **Seguimiento GPS:** ubicación en tiempo real durante la jornada, traza de rutas, visitas cumplidas,
  alertas de zona, organización por zonas y regiones.
- **Tareas y órdenes de trabajo:** asignación desde el mapa, subtareas, prioridades, estados
  (pendiente, asignada, preaprobada, finalizada, cancelada), evidencia de cierre con fotos y firma de un
  tercero, carga masiva desde Excel.
- **Relevamientos y formularios:** 13 tipos de pregunta, lógica condicional, autoevaluación con puntaje,
  generación automática de documentos, portales para supervisores y clientes; funcionan offline.
- **Flujos de procesos:** fases encadenadas o condicionales, responsables por fase, notificaciones.
- **Novedades y auditorías:** fotos con etiquetas, offline, auditorías planificadas, acceso para el
  cliente final.

### Comunicación y Datos — [comunicacion-y-datos.html](https://browix.com/comunicacion-y-datos.html)

- **Comunicación interna:** mensajes ilimitados con informe de lectura, noticias con reacciones,
  cumpleaños y aniversarios automáticos, push con ruteo inteligente.
- **Métricas e informes:** dashboards en tiempo real, exportación a Excel y PDF.
- **Importación y respaldo:** importación masiva desde Excel, backup automático e ilimitado en la nube,
  campos personalizados, estructura multiempresa.
- **API e integraciones:** API para el sistema de liquidación, ERP o herramientas internas
  (ej. `GET /api/v1/intervals`, `POST /api/v1/users`).

### Asistente IA — [ia.html](https://browix.com/ia.html)

- Responde 24/7 a los empleados desde la app, solo con la base de conocimiento cargada por la empresa,
  citando la fuente; consulta datos vivos del propio empleado (ej. saldo de vacaciones).
- Si no puede resolver, abre un **ticket** al área correcta (RRHH, Legales…) con seguimiento completo.
- Repositorio de temas/subtemas, modo prueba con tester, reindexado automático.
- Analítica de contención (ej. 82% resuelto sin intervención humana), brechas de contenido, auditoría
  completa de conversaciones.

## Experiencia por rol

- **Panel web** para administrar.
- **App para Empleado:** fichaje, recibos y documentos, solicitudes, tareas, capacitaciones, uniformes,
  Asistente IA.
- **App para Supervisor:** todo lo anterior + fichadas del equipo en tiempo real, discrepancias,
  aprobación de solicitudes, alta de tareas.
- **Checkpoint:** cualquier tablet como reloj de fichado (identificación numérica + foto, detección de
  rostro, 100% offline, multisucursal), a una fracción del costo de un reloj tradicional.

## Casos de uso — [casos-de-uso.html](https://browix.com/casos-de-uso.html)

| Rubro | Qué resuelve |
| --- | --- |
| [Limpieza y mantenimiento](https://browix.com/casos-de-uso.html#limpieza) | Fichaje en cada servicio, aviso inmediato de ausencias, horas contratadas vs. cubiertas para facturar sin discusión |
| [Seguridad y vigilancia](https://browix.com/casos-de-uso.html#seguridad) | Turnos 4x1/5x2/14x14/12x24, dotación mínima por objetivo, biometría antifraude, vencimiento de credenciales |
| [Logística y mensajería](https://browix.com/casos-de-uso.html#logistica) | Fichaje desde la calle, prueba de entrega con foto/GPS/firma, traza de rutas |
| [Trade marketing y ventas](https://browix.com/casos-de-uso.html#trade) | Relevamientos en góndola, puntos sin visitar, reportes para las marcas |
| [Multisucursal, franquicias y gastronomía](https://browix.com/casos-de-uso.html#multisucursal) | Una tablet por sucursal, cierre de mes sin Excel, recibos sin repartir sucursal por sucursal |
| [Constructoras](https://browix.com/casos-de-uso.html#construccion) | Fichaje sin internet en obra, horas imputadas por obra, legajo con vencimientos, EPP con comprobante |
| [Otras industrias](https://browix.com/casos-de-uso.html#otras) | Cualquier empresa con personal a cargo |

## Implementación, soporte y precio

- Implementación guiada por un especialista (carga de empleados, ubicaciones y jornadas).
- Sin costos ocultos de puesta en marcha: "lo que acordás es lo que pagás, mes a mes, sin contratos que
  te anclen".
- Soporte sin límite de horas con ejecutivo de cuenta; Asistente IA 24/7, manuales y videotutoriales.
- **Precio:** licencias mensuales en pesos. El sitio **no publica montos** → el agente nunca da cifras;
  lo cotiza el asesor en la demo.

## Seguridad

Firma con validez legal (Ley 25.506, Res. 346/2019) · datos cifrados · respaldo en la nube · permisos
por rol (administradores, supervisores, empleados y terceros).

## Contacto y demo — [contacto.php](https://browix.com/contacto.php)

- Formulario: nombre, teléfono, empresa, cantidad de empleados, email, motivo ("Asesoramiento
  comercial / demo" o "Mesa de ayuda / soporte técnico") y mensaje.
- **Qué esperar de la demo:** reunión con un asesor en el horario del interesado, Browix aplicado a su
  tipo de operación, respuestas sobre precios y puesta en marcha.
- **Clientes actuales con soporte técnico:** "Mesa de ayuda" en el formulario o info@browix.com.

## Reglas del agente (resumen de `app/prompts.py`)

- Responder primero la consulta del interesado (1–3 frases) y después seguir el cuestionario, una
  pregunta por vez, salteando lo que ya haya contado solo.
- Solo lo que está en la base de conocimiento; lo demás se anota para que el asesor lo confirme.
- **Nunca** dar precios, prometer fechas de demo, pedir contraseñas o datos de tarjeta, ni mencionar la
  evaluación del lead.
- Soporte técnico de clientes actuales → derivar a Mesa de ayuda / info@browix.com.
- Salida apta para TTS: sin siglas (salvo GPS, PIN, PDF, API, Excel), números en palabras, correos
  dichos ("info arroba browix punto com").

## Links relevados

- https://browix.com/
- https://browix.com/tiempo-y-presentismo.html (`#presentismo`, `#jornadas`)
- https://browix.com/gestion-de-personas.html (`#recibos`, `#legajo`, `#seleccion`, `#capacitaciones`, `#uniformes`)
- https://browix.com/operaciones-en-terreno.html (`#tareas`, `#relevamientos`, `#flujos`, `#novedades`)
- https://browix.com/comunicacion-y-datos.html (`#comunicacion`)
- https://browix.com/ia.html
- https://browix.com/casos-de-uso.html
- https://browix.com/contacto.php

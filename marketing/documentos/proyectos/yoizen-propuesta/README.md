# Propuesta de integración para Yoizen

- **Pedido (20-oct-2026, Laureano):** un PDF con el overview y la propuesta de integración, con la fuente y los
  colores de la marca, un diagrama de la integración y texto explicativo orientado a negocio, no técnico. Dos hojas
  como máximo, con el 0800 y el link web.
- **Destinatario:** Juan Stamati (Yoizen), para llevarlo a su revisión interna con el CTO y producto. Contexto de la
  reunión y video técnico que lo acompaña: [`../../../videos/proyectos/yoizen/`](../../../videos/proyectos/yoizen/README.md).
- **Formato:** A4, 2 hojas. `make doc P=yoizen-propuesta V=<n> HOJAS=2`.

## Estructura (v1)

1. **Hoja 1, overview:** título "Voz para los agentes que Yoizen ya tiene", cuatro cifras, el problema de sumar voz
   frente a lo que aporta Atentina, y el diagrama (clientes → Yoizen por chat, → Atentina por llamadas; Yoizen ⇄
   Atentina por Agentes, Llamadas, Voz para bots y Datos).
2. **Hoja 2, propuesta:** tres formas de integrarse con un ejemplo cada una, qué gana Yoizen, quién hace qué,
   próximos pasos (los de la reunión), nota sobre otros países y el pie de contacto.

## Afirmaciones y de dónde salen

- **0,9 s y "9 de cada 10 respuestas en menos de 1,5 s":** 35 turnos de llamadas reales desde el 7-oct-2026
  (`call_logs.latency`): 57 % < 1 s, 91 % < 1,5 s, 100 % < 2 s.
- **"4 en 1"** en lugar de "100 % propio": la telefonía es de Anura.
- **Omitido:** "hasta 60 llamadas simultáneas" (queda como "capacidad" a medir en el piloto).
- **A validar:** "piloto sin costo" (lo ofreció Laureano en la reunión); campañas programadas sin desplegar; la
  conexión con su Asterisk es una tarea pendiente.

## Versiones

| Versión | Fecha | Qué cambió | Estado |
|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 20-oct-2026 | Primera versión | borrador |

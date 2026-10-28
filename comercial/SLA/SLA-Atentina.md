<!--
NOTAS INTERNAS (borrar antes de enviar)
- Borrador. Revisar con abogado comercial antes de firmar, en especial §10 (créditos) y §12 (limitación de responsabilidad).
- Completar todos los campos entre [CORCHETES]: razón social, CUIT, horario hábil, teléfono de guardia y URL de la Página de Estado (hoy no existe; evaluar un status.atentina.com.ar).
- Tiempos de soporte (§8) y RPO/RTO (§9): ajustar a lo que el equipo realmente puede cubrir, en particular la guardia 24/7 para Severidad 1 y la redundancia de dos sitios (hoy la plataforma corre en un solo server; ver docs/PRODUCCION.md).
- 99,8% mensual = ~86 min de indisponibilidad permitida en un mes de 30 días.
-->

# Acuerdo de Nivel de Servicio (SLA)

**Atentina**
Versión 1.0 — Vigente desde: [FECHA]

---

## 1. Objeto y alcance

El presente Acuerdo de Nivel de Servicio ("SLA") establece los compromisos de disponibilidad, soporte y comunicación de incidentes que [RAZÓN SOCIAL] (CUIT [CUIT]), en adelante "Atentina", asume frente al Cliente respecto de la plataforma de atención telefónica y por WhatsApp con agentes de voz de Atentina (el "Servicio").

Este SLA forma parte integrante del contrato de servicio o de los Términos y Condiciones suscriptos entre Atentina y el Cliente (el "Contrato"). En caso de contradicción, prevalece el Contrato, salvo en lo referido específicamente a niveles de servicio y créditos.

## 2. Definiciones

- **Servicio Principal:** las funciones críticas de la plataforma, que son:
  - inicio de sesión y autenticación;
  - la aplicación web (el panel en `app.atentina.com.ar`);
  - la API pública (`/api/v1`);
  - el agente de voz telefónico: recepción y originación de llamadas (reconocimiento de voz, modelo de lenguaje y síntesis de voz) en los números asignados al Cliente;
  - la creación y consulta de agentes, números y llamadas.
- **Servicios Complementarios:** la mensajería de WhatsApp (entrante y campañas salientes), reportes, exportaciones y la demo pública de la landing. Se informan en la Página de Estado pero no computan para el cálculo de Disponibilidad.
- **Página de Estado:** el sitio público [URL PÁGINA DE ESTADO], alojado en infraestructura independiente de la plataforma. Muestra en tiempo real el estado de cada componente, el historial de incidentes y la Disponibilidad del mes en curso.
- **Minuto de Indisponibilidad:** todo minuto en que el Servicio Principal no responde correctamente a los chequeos automáticos realizados desde al menos dos (2) de tres (3) o más ubicaciones geográficas independientes. "No responder correctamente" incluye:
  - error de conexión;
  - código HTTP 5xx;
  - tiempo de respuesta superior a 30 segundos;
  - una llamada de prueba a un número de control que no conecta o no recibe el saludo inicial del agente dentro de los 30 segundos.
- **Mes Calendario:** período comprendido entre el día 1 a las 00:00 y el último día del mes a las 23:59, hora oficial de Argentina (UTC−3).
- **Abono Mensual:** el importe neto de impuestos efectivamente facturado al Cliente por el Servicio en el Mes Calendario afectado.
- **Incidente:** todo evento no planificado que interrumpe o degrada el Servicio.

## 3. Compromiso de disponibilidad

Atentina se compromete a que el Servicio Principal tenga una **Disponibilidad Mensual igual o superior al 99,8%** en cada Mes Calendario.

Como referencia, el 99,8% equivale a un máximo aproximado de **1 hora y 26 minutos** de indisponibilidad en un mes de 30 días.

## 4. Medición

4.1. La Disponibilidad Mensual se calcula según la siguiente fórmula:

```
Disponibilidad (%) = (Minutos del Mes − Minutos de Indisponibilidad) / Minutos del Mes × 100
```

Los minutos alcanzados por las exclusiones de la Sección 5 no se consideran Minutos de Indisponibilidad.

4.2. La medición la realiza un sistema de monitoreo externo e independiente de la infraestructura del Servicio:
- los chequeos a la aplicación web y a la API se ejecutan cada sesenta (60) segundos, desde al menos tres (3) ubicaciones geográficas distintas, de las cuales al menos una está fuera de Argentina;
- además, se realiza al menos una llamada de prueba por hora a un número de control, para verificar el camino completo de telefonía (troncal SIP → LiveKit → agente de voz).

4.3. Los registros del sistema de monitoreo y la Página de Estado constituyen la fuente oficial de medición. Si el Cliente dispone de registros propios (por ejemplo, de su propia central o CRM) que muestren una discrepancia, puede presentarlos junto con su reclamo y Atentina los analizará de buena fe.

## 5. Exclusiones

No se computarán como Minutos de Indisponibilidad los períodos en que la falta de disponibilidad sea consecuencia de:

1. **Mantenimiento Programado** realizado conforme a la Sección 6.
2. **Mantenimiento de seguridad urgente** notificado con al menos dos (2) horas de anticipación, hasta un máximo de sesenta (60) minutos por Mes Calendario. El excedente se computa como indisponibilidad.
3. **Causas atribuibles al Cliente**, entre ellas:
   - su conectividad, equipos, redes o software;
   - la configuración de su propia troncal SIP o central telefónica, si la conecta por ese medio;
   - el uso del Servicio en violación del Contrato o de la documentación técnica;
   - el exceso de los límites de uso pactados en su plan (minutos, números o llamadas concurrentes).
4. **Servicios de terceros** que no están bajo el control de Atentina, como la plataforma de mensajería de WhatsApp (Meta), pasarelas de pago, proveedores de email o servicios de DNS del Cliente. Esta exclusión no alcanza a los proveedores de infraestructura contratados por Atentina para operar el Servicio Principal (troncal SIP, LiveKit, hosting).
5. **Caso fortuito o fuerza mayor**, en los términos del art. 1730 del Código Civil y Comercial de la Nación, incluyendo desastres naturales, actos de autoridad pública, conflictos bélicos y cortes generalizados de energía o telecomunicaciones que excedan las medidas de contingencia razonables de Atentina.
6. **Ataques maliciosos** (por ejemplo, denegación de servicio o fraude telefónico) de una magnitud que exceda las protecciones razonables vigentes, siempre que Atentina haya actuado con diligencia para mitigarlos.
7. **Suspensión del Servicio** dispuesta conforme al Contrato, por ejemplo por falta de pago o por uso indebido.
8. **Funciones en etapa beta, preliminar o de prueba**, identificadas como tales en la documentación del Cliente (por ejemplo, campañas salientes de WhatsApp o integraciones nuevas).

## 6. Mantenimiento programado

6.1. Atentina notificará los mantenimientos programados con al menos **setenta y dos (72) horas de anticipación**. La notificación se publicará en la Página de Estado y se enviará por email a los contactos técnicos registrados del Cliente.

6.2. Los mantenimientos programados (por ejemplo, actualización de los modelos de inferencia de voz, cambios en el reparto de GPU o actualizaciones de la plataforma de telefonía) se realizarán preferentemente entre las **00:00 y las 06:00 (UTC−3)**, en el horario de menor tráfico de llamadas, y no excederán **cuatro (4) horas por Mes Calendario**. El tiempo que exceda ese límite se computa como indisponibilidad.

6.3. Atentina procurará realizar los mantenimientos sin interrupción del Servicio, aprovechando su arquitectura redundante.

## 7. Comunicación de incidentes

7.1. Ante un Incidente que afecte al Servicio Principal, Atentina:
- publicará el Incidente en la Página de Estado dentro de los **quince (15) minutos** de detectado;
- actualizará su estado al menos cada **sesenta (60) minutos** hasta su resolución.

7.2. Los Clientes pueden suscribirse a las notificaciones de la Página de Estado por email, RSS o webhook.

7.3. Para todo Incidente de Severidad 1, Atentina publicará un **informe post-incidente** dentro de los **cinco (5) días hábiles** siguientes a su resolución. El informe incluirá:
- la cronología del Incidente;
- su causa raíz;
- su impacto (incluyendo, si corresponde, las llamadas o conversaciones de WhatsApp afectadas);
- las acciones correctivas y preventivas adoptadas.

## 8. Soporte técnico

8.1. **Canales:** email a [EMAIL SOPORTE] (`hola@atentina.com.ar`). Los Incidentes de Severidad 1 pueden reportarse además por [CANAL URGENTE / TELÉFONO].

8.2. **Horario hábil:** lunes a viernes de [09:00 a 18:00] (UTC−3), excepto feriados nacionales.

8.3. **Tiempos de primera respuesta:**

| Severidad | Descripción | Primera respuesta | Cobertura |
|---|---|---|---|
| **1 — Crítica** | El agente de voz no puede originar ni recibir llamadas, o hay pérdida de datos (llamadas, transcripciones o mensajes), para todos o la mayoría de los Clientes | 1 hora | 24×7 |
| **2 — Alta** | Función importante degradada o no disponible sin alternativa razonable (por ejemplo, demoras altas del agente en un número, o la integración de WhatsApp caída) | 4 horas hábiles | Horario hábil |
| **3 — Media** | Falla parcial con alternativa disponible, o error que no impide operar (por ejemplo, un reporte que no exporta) | 1 día hábil | Horario hábil |
| **4 — Baja** | Consultas, solicitudes de mejora o errores menores | 3 días hábiles | Horario hábil |

8.4. Los tiempos de primera respuesta son compromisos de atención, no de resolución. Atentina trabajará de forma continua en los Incidentes de Severidad 1 hasta su resolución o mitigación.

## 9. Respaldo y continuidad

9.1. El Servicio opera sobre infraestructura redundante distribuida en al menos dos (2) sitios físicos independientes. Cada sitio cuenta con:
- alimentación eléctrica respaldada por UPS;
- conectividad dual (fibra óptica y enlace satelital).

9.2. Los datos del Cliente (definiciones de agentes, historial y grabaciones de llamadas, transcripciones y mensajes de WhatsApp) se replican entre sitios. Además, se respaldan diariamente en una ubicación externa a ambos sitios y se conservan durante [30] días.

9.3. **Objetivos de recuperación** ante un desastre que afecte a un sitio completo:
- **RPO** (pérdida máxima de datos): [1 hora].
- **RTO** (tiempo máximo de restablecimiento): [4 horas].

Estos objetivos son de mejor esfuerzo y no generan créditos por sí mismos. El tiempo de indisponibilidad resultante sí computa para la Disponibilidad Mensual.

## 10. Créditos de servicio

10.1. Si la Disponibilidad Mensual del Servicio Principal resulta inferior al 99,8%, el Cliente tendrá derecho a los siguientes créditos, calculados sobre el Abono Mensual del mes afectado:

| Disponibilidad Mensual | Crédito |
|---|---|
| Menor a 99,8% e igual o mayor a 99,0% | 10% |
| Menor a 99,0% e igual o mayor a 95,0% | 25% |
| Menor a 95,0% | 50% |

10.2. Los créditos:
- **se aplicarán como descuento en la facturación siguiente** y no son reembolsables en efectivo, salvo que el Contrato haya finalizado sin facturación pendiente;
- **no podrán superar en ningún caso el 50% del Abono Mensual** del mes afectado;
- no son transferibles ni acumulables con otras bonificaciones por el mismo evento;
- solo corresponden si el Cliente se encuentra al día con sus pagos al momento del reclamo.

10.3. **Los créditos de servicio constituyen el único y exclusivo remedio del Cliente por el incumplimiento de los niveles de disponibilidad** establecidos en este SLA, sin perjuicio de lo dispuesto en la Sección 12.

## 11. Procedimiento de reclamo

11.1. Para obtener un crédito, el Cliente debe enviar un reclamo a [EMAIL SOPORTE] (`hola@atentina.com.ar`) dentro de los **treinta (30) días corridos** posteriores al cierre del Mes Calendario afectado, con la siguiente información:
- razón social e identificación de la cuenta (cliente y número afectado);
- fechas y horarios aproximados de la indisponibilidad;
- descripción del impacto (llamadas o mensajes afectados) y, si los tuviera, registros o evidencia propios.

11.2. Atentina responderá el reclamo dentro de los **diez (10) días hábiles** de recibido. Si el reclamo es procedente, aplicará el crédito en la factura siguiente.

11.3. Los reclamos presentados fuera de plazo no generarán derecho a crédito.

## 12. Limitación de responsabilidad

12.1. Ninguna de las partes será responsable frente a la otra por daños indirectos o consecuenciales. Se incluyen, entre otros:
- lucro cesante;
- pérdida de oportunidades de negocio;
- pérdida de chance;
- daño reputacional.

12.2. La responsabilidad total de Atentina derivada del Contrato y de este SLA, por cualquier causa, **no excederá el monto total efectivamente abonado por el Cliente durante los doce (12) meses anteriores** al hecho que origine el reclamo.

12.3. Las limitaciones de esta Sección **no se aplicarán** en los siguientes casos:
- daños causados por dolo o culpa grave;
- incumplimiento de las obligaciones de confidencialidad;
- incumplimiento de la normativa de protección de datos personales (Ley 25.326);
- cualquier otro supuesto en que la ley aplicable no permita limitar la responsabilidad.

## 13. Seguridad y confidencialidad

Atentina trata las grabaciones, transcripciones, definiciones de agentes y demás datos cargados o generados por el Cliente dentro de la plataforma como información confidencial, conforme a las cláusulas de confidencialidad del Contrato. Aplica medidas técnicas y organizativas razonables para protegerlos, entre ellas:
- cifrado en tránsito;
- cifrado en reposo de credenciales de integraciones de terceros (por ejemplo, tokens de WhatsApp);
- control de acceso por roles;
- registro de accesos.

Ante un incidente de seguridad que afecte datos del Cliente, Atentina lo notificará sin demora injustificada y, en lo posible, dentro de las **setenta y dos (72) horas** de tomado conocimiento.

## 14. Modificaciones

Atentina podrá modificar este SLA notificando al Cliente con al menos **treinta (30) días** de anticipación. Las modificaciones que reduzcan los niveles de servicio no se aplicarán durante el plazo de vigencia contratado en curso, salvo acuerdo expreso del Cliente.

## 15. Ley aplicable y jurisdicción

Este SLA se rige por las leyes de la República Argentina. Para cualquier controversia, las partes se someten a los tribunales ordinarios de la ciudad de Córdoba, con renuncia a cualquier otro fuero o jurisdicción.

---

## Anexo A — Equivalencias de disponibilidad

| Disponibilidad | Indisponibilidad máxima (mes de 30 días) |
|---|---|
| 99,8% (compromiso) | ~1 h 26 min |
| 99,0% | ~7 h 12 min |
| 95,0% | ~36 h |

## Anexo B — Contactos

| Rol | Contacto |
|---|---|
| Soporte técnico | `hola@atentina.com.ar` |
| Incidentes críticos (Sev. 1) | [CANAL URGENTE / TELÉFONO] |
| Página de Estado | [URL PÁGINA DE ESTADO] |
| Comercial / reclamos de créditos | `hola@atentina.com.ar` |

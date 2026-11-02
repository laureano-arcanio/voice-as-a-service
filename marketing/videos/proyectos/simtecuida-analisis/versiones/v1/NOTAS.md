# simtecuida-analisis · v1

Estado: borrador

- **Archivo:** `simtecuida-analisis-v1.mp4` · 59,6 s (1789 cuadros) · −15,5 LUFS · 7,5 MB (`make video-revisar
  P=simtecuida-analisis V=1 ARGS="--tramos 0,5.6,12.2,20.9,35.55,45.05,48.8,49.85,56.25"`).
- **Pedido (2-nov-2026, textual):** "con esta información hago un video con el template que venimos usando en formato blanco.
  No utilizamos más el color azul oscuro para los fondos, y que incluya toda la información directamente enfocado en la solución
  que le vamos a dar, con una pequeña introducción de lo que vimos de su empresa y dónde están las oportunidades, y luego el
  diagrama como hemos hecho en otras situaciones, similar a lo que tenemos en la landing page. Unos 60 segundos de duración
  máximo."
- **Qué cambió:** primera versión. Respecto de las plantillas (`goldman-analisis` v3, `baicenter-analisis` v1): sin intro ni
  cierre oscuros, sin encabezado de maqueta ni píldora oscura, logo oscuro; el diagrama con el lenguaje de los videos de la home.
- **Locución** (mejor de 4 tomas, a 1×; entre paréntesis, fidelidad con el STT):
  - a1 paula "En SIM Te Cuida vimos atención a toda hora, en CABA y GBA, y asignación en dos a cuatro horas." (0,99)
  - a2 paula "Todo entra por un mismo canal. Reconocer al cliente, y separar lo urgente, ayudaría a cumplir esa promesa." (1,00)
  - a3 paula "Un agente con IA atiende a toda hora su línea, el cero ochocientos y el WhatsApp. Lo que necesita una persona pasa a su equipo, y todo queda en el panel." (1,00)
  - a4a paula "Reconoce a quien llama por su teléfono. Si no aparece, pide nombre, DNI u otro dato de contacto." (1,00)
  - a4b paula "Si detecta una posible emergencia, le da prioridad. Y deriva a su equipo, por rotación." (1,00)
  - a4c gonzalo "Prioriza la atención: no es un servicio de emergencias." (1,00)
  - a5a paula "Sus clientes se cargan en la misma plataforma, con teléfono, suscripción y cuidados." (1,00)
  - a5b paula "Antes de atender, su equipo oye una minuta. Quien llama, no la oye." (1,00)
  - a6 paula "En el panel ven quién tomó cada consulta, y cuánto tardó." (1,00)
  - a7 gonzalo "Plan Mostrador, más mantenimiento del CRM: treinta y nueve mil pesos por mes." (1,00)
  - a8 paula "¿Agendamos una reunión personalmente?" (1,00)
- **Pronunciación (STT, falta confirmar de oído):** "SIM Te Cuida" se oye "SimTecuida"; "DNI", "DNI"; "cero ochocientos",
  "0800"; "CABA", "Cava" (mismo sonido). Sin grafías forzadas.
- **Cambios de texto medidos:** "Quien llama, no." en el video mezclado dio "¿Quién llama o no?": pasó a "Quien llama, no la
  oye." "u otro dato." dejó una pausa rara antes del final: volvió a "u otro dato de contacto."
- **Controles:**
  - Cuadros y hojas de cada 2 s: sin texto cortado ni superposiciones (corregidos antes del render: título de la ficha en dos
    líneas, cliente pegado a la suscripción).
  - Sin fondos oscuros: cuadro por cuadro (1789), luminancia media mínima 237 de 255; a lo sumo 1,09 % de píxeles oscuros
    (texto); esquinas ≥ 247; primer cuadro, 255. Ningún `C.ink` como fondo y sin `atentina-logo-blanco` en `src/`.
  - Volumen −15,5 LUFS. Primero dio −14,5: −1 dB en los WAV con ffmpeg, sin nuevos pedidos al TTS, y `ganancia_db` −1 en el guion.
  - Transcripción por tramos: fiel en todas las escenas; finales de frase completos; solo música en el tramo 48,8–49,85.
  - Afirmaciones contra el PDF v2 y la hoja del PDF v1: ver el README.
- **A revisar antes de mostrarlo afuera:**
  - Escuchar "SIM Te Cuida", "CABA", "DNI" y "cero ochocientos".
  - Funciones no construidas: ver el README. El video las vende, como el PDF.
  - Plan Mostrador tiene hoy 1 llamada a la vez y derivación a 1 o 2 personas (`simtecuida.md`, 7.4 y 7.6), y el video muestra
    una rotación por $ 39.000; la aclaración de capacidad queda en pantalla.
  - Oportunidades: lecturas nuestras, a confirmar con SIM.

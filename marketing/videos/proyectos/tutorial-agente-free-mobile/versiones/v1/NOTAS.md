Estado: borrador

# Tutorial agente Free en el celular v1

## Pedido

> crear un video de cómo crear un agente y cómo probarlo desde la vista mobile para un plan free. El workflow:
> iniciar la aplicación, ir a Agentes, crear un agente básico, por ejemplo para un restaurante con algunas opciones
> de precios. Mostrar también que se puede copiar el link y compartirlo para que otras personas lo usen, que no
> necesitan hacer nada más, y que con eso ya pueden atender llamadas y ver las transcripciones en el portal.
> Explicar también que las funcionalidades más avanzadas, como transferencias de llamadas y registro de pedidos,
> turnos, etc., están en los planes Mostrador y Central. Un video corto y práctico.

## Qué es

Primera versión. Vertical 1080 × 1920, 62,5 s, 10,2 MB. Diez escenas: intro, Agentes, nombre, definición con la
base de conocimiento y precios, probar desde el navegador, link para llamar, la página que abre quien llama,
Conversaciones con la transcripción, planes pagos y cierre. Guion en el README.

## Locución

- `paula`, 4 tomas por línea, la más fiel (0,99–1,00). `ganancia_db: -1.5`. Total de voz: 51,9 s.
- Duraciones: f1 4,48 · f2 4,32 · f3 4,88 · f4 6,08 · f5 6,48 · f6 5,12 · f7 5,20 · f8 5,36 · f9 7,68 ·
  f10 2,32 s. Ninguna se pisa con la escena siguiente.
- f9 se regeneró: con "viene en los planes pagos, de Mostrador a Central" el STT oyó "Demostradora central";
  quedó "están los planes pagos: Mostrador, Sucursal y Central" (además, más fiel a los tiers).

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de prueba (`scratch/videos/tafm/stills/`) y hojas de `make video-revisar`
  (`scratch/videos/revision/tutorial-agente-free-mobile-v1/`): sin textos cortados; se corrigió un toque mal ubicado
  en el campo Rol.
- **−15,9 LUFS** (referencia −16 ± 1,5).
- Transcripción por tramos: las diez líneas se entienden. El STT oye "probar a gente" (f5) y "tu primera gente"
  (f10) por "agente": confusión habitual del STT, a confirmar de oído.

## A revisar antes de mostrarlo afuera

- **"Registro de pedidos, turnos" no se dice:** ningún tier lo incluye ni lo bloquea. Registrar pedidos o turnos
  en un sistema es una app o integración que asigna el admin (`docs/APPS.md`), no un campo del plan. Si se quiere
  decir, hay que definir en qué planes se ofrece.
- **"Mostrador y Central" del pedido → "Mostrador, Sucursal y Central":** las derivaciones, el número y WhatsApp
  están en los tres. Central no se vende por el panel (no aparece en Planes) y en la landing el plan grande es
  "Red": conviene unificar el nombre.
- **Funciones por plan** (candados, aviso de Equipo, "Free" en el menú): la migración 0025 está en producción, pero
  la UI se capturó del working tree con cambios sin commitear de otra sesión; revisar que el panel desplegado se vea
  igual.
- **Datos ilustrativos:** El Fogón, Marta, los precios, el mensaje con el link, el token, la llamada de prueba, la
  llamada por el link y las conversaciones (mocks).
- **Link para llamar:** falta una llamada real de punta a punta (LINK_LLAMADA_PLAN, sección 11). El Free tiene un
  solo link y 20 minutos entrantes por mes, que se dice en pantalla.
- Mobile: la tabla de Conversaciones se corta a la derecha (columnas fuera de la vista), como en `derivaciones`.

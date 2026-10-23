# Marketing: videos y documentos

Piezas de comunicación de Atentina, una carpeta por proyecto y una carpeta por versión, cada una con sus notas.

| Qué | Dónde | Cómo se hace | Agente |
|---|---|---|---|
| Videos animados con locución del TTS propio | [`videos/`](videos/) | [`docs/VIDEOS.md`](../docs/VIDEOS.md) | [`videos`](../.claude/agents/videos.md) |
| Documentos (propuestas, overviews, fichas) en PDF | [`documentos/`](documentos/) | [`docs/DOCUMENTOS.md`](../docs/DOCUMENTOS.md) | [`documentos`](../.claude/agents/documentos.md) |

## Proyectos

| Proyecto | Tipo | Para | Última versión |
|---|---|---|---|
| [`general`](videos/proyectos/general/README.md) | Video, ~60 s | Empresas (landing, redes, primer contacto) | v2, borrador |
| [`yoizen`](videos/proyectos/yoizen/README.md) | Video técnico, ~70 s | Yoizen (integradores) | v1, borrador |
| [`transcripcion`](videos/proyectos/transcripcion/README.md) | Video, ~42 s | Call centers (transcripción y voz) | v1, borrador |
| [`goldman`](videos/proyectos/goldman/README.md) | Video, ~40 s | Isaías Goldman SA (prospecto, climatización, Córdoba) | v3, borrador |
| [`goldman-analisis`](videos/proyectos/goldman-analisis/README.md) | Video, ~60 s | Isaías Goldman SA (el PDF en video: lo que hacen bien, lo que observamos, la propuesta) | v2, borrador |
| [`yoizen-propuesta`](documentos/proyectos/yoizen-propuesta/README.md) | PDF, 2 hojas | Yoizen (revisión interna) | v1, borrador |
| [`goldman-propuesta`](documentos/proyectos/goldman-propuesta/README.md) | PDF, 5 hojas | Isaías Goldman SA (Isaías, Jonatan y Carolina) | v1, borrador |
| [`baicenter-analisis`](videos/proyectos/baicenter-analisis/README.md) | Video, ~65 s | BAIC Center / Grupo Signature (el PDF en video: lo que hacen bien, áreas a mejorar, la propuesta) | v1, borrador |
| [`baicenter-propuesta`](documentos/proyectos/baicenter-propuesta/README.md) | PDF, 5 hojas | BAIC Center / Grupo Signature (Edgardo Fernández Favaron) | v2, borrador |
| [`sqlamoblamientos-propuesta`](documentos/proyectos/sqlamoblamientos-propuesta/README.md) | PDF, 5 hojas | SQL Amoblamientos (Pilar Conte; Jorge Urizar y sus hijos) | v2, borrador |
| [`sqlamoblamientos-analisis`](videos/proyectos/sqlamoblamientos-analisis/README.md) | Video, ~70 s | SQL Amoblamientos (el PDF en video: lo que hacen bien, dónde podríamos mejorar con Atentina, la propuesta) | v6 (prueba de voz con paula), borrador; v5 con lucas |
| [`cimepa-propuesta`](documentos/proyectos/cimepa-propuesta/README.md) | PDF, 5 hojas | CIMEPA S.A. (Pablo; propuesta técnica y de integración) | v1, borrador |
| [`axiomait-propuesta`](documentos/proyectos/axiomait-propuesta/README.md) | PDF, 6 hojas | Axioma IT Solutions (Axel Díaz; propuesta técnica para un integrador) | v1, borrador |
| [`cimepa-analisis`](videos/proyectos/cimepa-analisis/README.md) | Video, ~65 s | CIMEPA S.A. (Pablo; el PDF técnico en video: lo que pidieron, los tres flujos de llamada, el registro y su agente; v2 con paula y pablo) | v2, borrador |
| [`axiomait-analisis`](videos/proyectos/axiomait-analisis/README.md) | Video, ~77 s | Axioma IT Solutions (Axel Díaz; el PDF técnico en video: lo que hacen, dónde encaja la voz, el producto, el llamador del CRM, voces y naturalidad; paula y lucas) | v1, borrador |
| [`zennonbi-propuesta`](documentos/proyectos/zennonbi-propuesta/README.md) | PDF, 5 hojas | Zennon BI (Cristian Ventura; propuesta de alianza e integración con Dynamics 365 y Power Platform) | v1, borrador |
| [`zennonbi-analisis`](videos/proyectos/zennonbi-analisis/README.md) | Video, ~76 s | Zennon BI (Cristian Ventura; el PDF de alianza en video: lo que hacen, dónde encaja la voz, la integración por Power Automate, el módulo en sus KickStart con el tablero ilustrativo y la puesta en marcha; paula y lucas) | v1, borrador |
| [`propuesta-atentina`](documentos/proyectos/propuesta-atentina/README.md) | PDF, 3 hojas | Genérico (cualquier prospecto) | v1, borrador |

## Convención

- `proyectos/<slug>/README.md`: el pedido, el público, el mensaje, el contenido, las afirmaciones con su fuente y
  la tabla de versiones.
- `proyectos/<slug>/versiones/vN/`: la pieza (MP4 o PDF), `NOTAS.md` (`Estado: borrador` o `Estado: cerrada`, el
  pedido que la originó, qué cambió y los controles) y, al cerrarla, `fuente/`.
- Una versión cerrada no se vuelve a generar: un cambio es una versión nueva (`make video-cerrar`, `make doc-cerrar`).
- Los MP4 y la música no se versionan en git (se regeneran); el resto sí.

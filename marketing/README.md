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
| [`propuesta-atentina`](documentos/proyectos/propuesta-atentina/README.md) | PDF, 3 hojas | Genérico (cualquier prospecto) | v1, borrador |

## Convención

- `proyectos/<slug>/README.md`: el pedido, el público, el mensaje, el contenido, las afirmaciones con su fuente y
  la tabla de versiones.
- `proyectos/<slug>/versiones/vN/`: la pieza (MP4 o PDF), `NOTAS.md` (`Estado: borrador` o `Estado: cerrada`, el
  pedido que la originó, qué cambió y los controles) y, al cerrarla, `fuente/`.
- Una versión cerrada no se vuelve a generar: un cambio es una versión nueva (`make video-cerrar`, `make doc-cerrar`).
- Los MP4 y la música no se versionan en git (se regeneran); el resto sí.

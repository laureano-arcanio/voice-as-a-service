import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { f } from "../../../src/comun/montaje";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { DUR, IDS, LEAD, SCENES, SUBS, type SceneId } from "./timeline";

const DIR = "proyectos/yoizen-tu-propio-agente";
/** Diapositivas con fondo oscuro (portada y cierre): el pie se tapa con el mismo color. */
const OSCURAS: SceneId[] = ["s01", "s12"];

/**
 * Una diapositiva de la presentación (PNG de 1920 × 1080 de documentos/proyectos/yoizen-tu-propio-agente v1),
 * con una entrada suave (sube 14 px) y un zoom muy leve a lo largo de la escena. El título del pie
 * ("Atentina × Yoizen · Tu propio agente") se tapa con el fondo para dejar lugar a los subtítulos; el contador
 * ("n / 12", a la derecha) queda a la vista.
 */
export const Diapositiva: React.FC<{ id: SceneId }> = ({ id }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = f(SCENES[id].len);
  const y = interpolate(frame, [0, 0.6 * fps], [14, 0], { ...CLAMP, easing: EASE });
  const s = interpolate(frame, [0, len], [1, 1.012], CLAMP);
  const n = IDS.indexOf(id) + 1;
  const fondo = OSCURAS.includes(id) ? C.ink : C.bg;
  return (
    <AbsoluteFill style={{ background: fondo }}>
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${y}px) scale(${s})`, transformOrigin: "50% 50%" }}>
        <Img src={staticFile(`${DIR}/slides/${String(n).padStart(2, "0")}.png`)} style={{ width: 1920, height: 1080, display: "block" }} />
        {/* Tapa el título del pie (medido: x 112–616, y 998–1019); el contador de la derecha sigue a la vista */}
        <div style={{ position: "absolute", left: 100, width: 540, top: 996, height: 36, background: fondo }} />
      </div>
    </AbsoluteFill>
  );
};

export const ESCENAS: Record<SceneId, React.FC> = Object.fromEntries(IDS.map((id) => [id, () => <Diapositiva id={id} />])) as unknown as Record<SceneId, React.FC>;

/** Subtítulos de la locución, centrados en la línea del pie (como en tu-propio-agente, pero sin tapar el contador). */
export const Subtitulos: React.FC = () => {
  const frame = useCurrentFrame();
  let texto = "";
  let o = 0;
  for (const id of IDS) {
    const partes = SUBS[id];
    const ini = f(SCENES[id].from + LEAD);
    const len = f(DUR[id]);
    if (frame < ini || frame > ini + len + 6) continue;
    const total = partes.reduce((s, p) => s + p.length, 0);
    let acc = ini;
    for (const p of partes) {
      const d = (len * p.length) / total;
      if (frame >= acc && frame < acc + d + (p === partes[partes.length - 1] ? 6 : 0)) {
        texto = p;
        o = interpolate(frame, [ini, ini + 4, ini + len, ini + len + 6], [0, 1, 1, 0], CLAMP);
      }
      acc += d;
    }
  }
  if (!texto) return null;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 48, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{ background: "rgba(11,18,32,0.86)", color: "#fff", fontFamily: F.body, fontWeight: 600, fontSize: 27, lineHeight: 1.2,
        padding: "8px 22px", borderRadius: 12, maxWidth: 1380, textAlign: "center", whiteSpace: "nowrap" }}>
        {texto}
      </div>
    </div>
  );
};

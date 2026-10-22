import { Composition } from "remotion";
import { f, FPS } from "./comun/montaje";
import { TOTAL as GENERAL_TOTAL } from "../proyectos/general/src/timeline";
import { GeneralVideo } from "../proyectos/general/src/Video";
import { TOTAL as YOIZEN_TOTAL } from "../proyectos/yoizen/src/timeline";
import { YoizenVideo } from "../proyectos/yoizen/src/Video";
import { TOTAL as TRANSCRIPCION_TOTAL } from "../proyectos/transcripcion/src/timeline";
import { TranscripcionVideo } from "../proyectos/transcripcion/src/Video";
import { TOTAL as GOLDMAN_TOTAL } from "../proyectos/goldman/src/timeline";
import { GoldmanVideo } from "../proyectos/goldman/src/Video";
import { TOTAL as GOLDMAN_ANALISIS_TOTAL } from "../proyectos/goldman-analisis/src/timeline";
import { GoldmanAnalisisVideo } from "../proyectos/goldman-analisis/src/Video";
import { TOTAL as BAICENTER_ANALISIS_TOTAL } from "../proyectos/baicenter-analisis/src/timeline";
import { BaicenterAnalisisVideo } from "../proyectos/baicenter-analisis/src/Video";

// Una composición por proyecto, con el id igual a la carpeta de proyectos/ (lo usa `make video P=<id>`)
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="general" component={GeneralVideo} durationInFrames={f(GENERAL_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="yoizen" component={YoizenVideo} durationInFrames={f(YOIZEN_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="transcripcion" component={TranscripcionVideo} durationInFrames={f(TRANSCRIPCION_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="goldman" component={GoldmanVideo} durationInFrames={f(GOLDMAN_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="goldman-analisis" component={GoldmanAnalisisVideo} durationInFrames={f(GOLDMAN_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="baicenter-analisis" component={BaicenterAnalisisVideo} durationInFrames={f(BAICENTER_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
  </>
);

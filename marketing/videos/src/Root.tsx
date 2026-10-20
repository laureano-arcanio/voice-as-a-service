import { Composition } from "remotion";
import { f, FPS } from "./comun/montaje";
import { TOTAL as GENERAL_TOTAL } from "../proyectos/general/src/timeline";
import { GeneralVideo } from "../proyectos/general/src/Video";
import { TOTAL as YOIZEN_TOTAL } from "../proyectos/yoizen/src/timeline";
import { YoizenVideo } from "../proyectos/yoizen/src/Video";

// Una composición por proyecto, con el id igual a la carpeta de proyectos/ (lo usa `make video P=<id>`)
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="general" component={GeneralVideo} durationInFrames={f(GENERAL_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="yoizen" component={YoizenVideo} durationInFrames={f(YOIZEN_TOTAL)} fps={FPS} width={1920} height={1080} />
  </>
);

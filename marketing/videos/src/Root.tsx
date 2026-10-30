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
import { TOTAL as SQLAMOBLAMIENTOS_ANALISIS_TOTAL } from "../proyectos/sqlamoblamientos-analisis/src/timeline";
import { SqlamoblamientosAnalisisVideo } from "../proyectos/sqlamoblamientos-analisis/src/Video";
import { TOTAL as CIMEPA_ANALISIS_TOTAL } from "../proyectos/cimepa-analisis/src/timeline";
import { CimepaAnalisisVideo } from "../proyectos/cimepa-analisis/src/Video";
import { TOTAL as AXIOMAIT_ANALISIS_TOTAL } from "../proyectos/axiomait-analisis/src/timeline";
import { AxiomaitAnalisisVideo } from "../proyectos/axiomait-analisis/src/Video";
import { TOTAL as ZENNONBI_ANALISIS_TOTAL } from "../proyectos/zennonbi-analisis/src/timeline";
import { ZennonbiAnalisisVideo } from "../proyectos/zennonbi-analisis/src/Video";
import { TOTAL as PRIMEROS_PASOS_TOTAL } from "../proyectos/primeros-pasos/src/timeline";
import { PrimerosPasosVideo } from "../proyectos/primeros-pasos/src/Video";
import { TOTAL as DERIVACIONES_TOTAL } from "../proyectos/derivaciones/src/timeline";
import { DerivacionesVideo } from "../proyectos/derivaciones/src/Video";
import { TOTAL as TUTORIAL_AGENTE_FREE_MOBILE_TOTAL } from "../proyectos/tutorial-agente-free-mobile/src/timeline";
import { TutorialAgenteFreeMobileVideo } from "../proyectos/tutorial-agente-free-mobile/src/Video";
import { TOTAL as MCP_CLAUDE_CODE_TOTAL } from "../proyectos/mcp-claude-code/src/timeline";
import { McpClaudeCodeVideo } from "../proyectos/mcp-claude-code/src/Video";
import { TOTAL as API_DESARROLLADORES_TOTAL } from "../proyectos/api-desarrolladores/src/timeline";
import { ApiDesarrolladoresVideo } from "../proyectos/api-desarrolladores/src/Video";
import { TOTAL as LLAMADAS_SALIENTES_TOTAL } from "../proyectos/llamadas-salientes/src/timeline";
import { LlamadasSalientesVideo } from "../proyectos/llamadas-salientes/src/Video";
import { TOTAL as DOCS_INTRO_TOTAL } from "../proyectos/docs-intro/src/timeline";
import { DocsIntroVideo } from "../proyectos/docs-intro/src/Video";
import { TOTAL as TU_PROPIO_AGENTE_TOTAL } from "../proyectos/tu-propio-agente/src/timeline";
import { TuPropioAgenteVideo } from "../proyectos/tu-propio-agente/src/Video";
import { TOTAL as YOIZEN_TU_PROPIO_AGENTE_TOTAL } from "../proyectos/yoizen-tu-propio-agente/src/timeline";
import { YoizenTuPropioAgenteVideo } from "../proyectos/yoizen-tu-propio-agente/src/Video";
import { DURACION as META_REVIEW_MANAGEMENT_FRAMES, MetaReviewManagementVideo } from "../proyectos/meta-review-management/src/Video";
import { TOTAL as ATENCION_PUNTA_A_PUNTA_TOTAL } from "../proyectos/atencion-punta-a-punta/src/timeline";
import { AtencionPuntaAPuntaVideo } from "../proyectos/atencion-punta-a-punta/src/Video";
import { T as LANDING_AGENTE_T } from "../proyectos/landing-agente/src/timeline";
import { LandingAgenteVideo } from "../proyectos/landing-agente/src/Video";

// Una composición por proyecto, con el id igual a la carpeta de proyectos/ (lo usa `make video P=<id>`)
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="general" component={GeneralVideo} durationInFrames={f(GENERAL_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="yoizen" component={YoizenVideo} durationInFrames={f(YOIZEN_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="transcripcion" component={TranscripcionVideo} durationInFrames={f(TRANSCRIPCION_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="goldman" component={GoldmanVideo} durationInFrames={f(GOLDMAN_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="goldman-analisis" component={GoldmanAnalisisVideo} durationInFrames={f(GOLDMAN_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="baicenter-analisis" component={BaicenterAnalisisVideo} durationInFrames={f(BAICENTER_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="sqlamoblamientos-analisis" component={SqlamoblamientosAnalisisVideo} durationInFrames={f(SQLAMOBLAMIENTOS_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="cimepa-analisis" component={CimepaAnalisisVideo} durationInFrames={f(CIMEPA_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="axiomait-analisis" component={AxiomaitAnalisisVideo} durationInFrames={f(AXIOMAIT_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="zennonbi-analisis" component={ZennonbiAnalisisVideo} durationInFrames={f(ZENNONBI_ANALISIS_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="mcp-claude-code" component={McpClaudeCodeVideo} durationInFrames={f(MCP_CLAUDE_CODE_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="api-desarrolladores" component={ApiDesarrolladoresVideo} durationInFrames={f(API_DESARROLLADORES_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="atencion-punta-a-punta" component={AtencionPuntaAPuntaVideo} durationInFrames={f(ATENCION_PUNTA_A_PUNTA_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="llamadas-salientes" component={LlamadasSalientesVideo} durationInFrames={f(LLAMADAS_SALIENTES_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="docs-intro" component={DocsIntroVideo} durationInFrames={f(DOCS_INTRO_TOTAL)} fps={FPS} width={1920} height={1080} />
    <Composition id="tu-propio-agente" component={TuPropioAgenteVideo} durationInFrames={f(TU_PROPIO_AGENTE_TOTAL)} fps={FPS} width={1920} height={1080} />
    {/* Presentación para Yoizen con audio: las 12 diapositivas de documentos/proyectos/yoizen-tu-propio-agente */}
    <Composition id="yoizen-tu-propio-agente" component={YoizenTuPropioAgenteVideo} durationInFrames={f(YOIZEN_TU_PROPIO_AGENTE_TOTAL)} fps={FPS} width={1920} height={1080} />
    {/* Para la landing: sin locución, en loop */}
    <Composition id="landing-agente" component={LandingAgenteVideo} durationInFrames={f(LANDING_AGENTE_T.fin)} fps={FPS} width={1920} height={1080} />
    {/* App Review de Meta: capturas reales, subtítulos en inglés, sin locución */}
    <Composition id="meta-review-management" component={MetaReviewManagementVideo} durationInFrames={META_REVIEW_MANAGEMENT_FRAMES} fps={FPS} width={1920} height={1080} />
    {/* Vertical (9:16), para el celular */}
    <Composition id="primeros-pasos" component={PrimerosPasosVideo} durationInFrames={f(PRIMEROS_PASOS_TOTAL)} fps={FPS} width={1080} height={1920} />
    <Composition id="derivaciones" component={DerivacionesVideo} durationInFrames={f(DERIVACIONES_TOTAL)} fps={FPS} width={1080} height={1920} />
    <Composition id="tutorial-agente-free-mobile" component={TutorialAgenteFreeMobileVideo} durationInFrames={f(TUTORIAL_AGENTE_FREE_MOBILE_TOTAL)} fps={FPS} width={1080} height={1920} />
  </>
);

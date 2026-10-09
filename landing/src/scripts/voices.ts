import { synthesizeStream } from "./api";
import { int16ToFloat32, PCM_SAMPLE_RATE, PcmStreamPlayback } from "./pcm-player";
import { track } from "./analytics";
import { UserFacingError } from "./errors";

const BARS = 40;

function clock(seconds: number): string {
  const s = Number.isFinite(seconds) ? Math.max(0, Math.round(seconds)) : 0;
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function initVoices(root: HTMLElement) {
  const $ = <T extends Element = HTMLElement>(selector: string) => root.querySelector<T>(selector)!;
  const form = $<HTMLFormElement>("[data-voice-form]");
  const player = $("[data-player]");
  const play = $<HTMLButtonElement>("[data-play]");
  const text = $<HTMLTextAreaElement>("[data-text]");
  const count = $("[data-count]");
  const bars = $("[data-bars]");
  const progress = $("[data-progress]");
  const time = $("[data-time]");
  const error = $("[data-voice-error]");
  const more = $<HTMLButtonElement>("[data-more]");
  const lines = { f: root.dataset.lineF ?? "", m: root.dataset.lineM ?? "" };
  let edited = false;
  let context: AudioContext | null = null;
  let clip: { key: string; buffer: AudioBuffer } | null = null;
  // Lo que suena ahora: un audio ya generado (repetir) o el que llega mientras se sintetiza.
  let active: { elapsed: () => number; total: () => number; final: () => boolean; stop: () => void } | null = null;
  let frame = 0;
  let request: AbortController | null = null;

  for (let i = 0; i < BARS; i++) {
    const bar = document.createElement("i");
    bar.className =
      "block h-full max-w-[5px] flex-1 origin-center scale-y-[.06] rounded-xs bg-ink group-data-[state=playing]/player:animate-bar motion-reduce:group-data-[state=playing]/player:animate-none motion-reduce:group-data-[state=playing]/player:scale-y-(--h)";
    bar.style.setProperty("--d", `${(0.35 + Math.random() * 0.5).toFixed(2)}s`);
    bar.style.setProperty("--o", `${(-Math.random()).toFixed(2)}s`);
    bar.style.setProperty("--h", (0.3 + Math.random() * 0.7).toFixed(2));
    bars.appendChild(bar);
  }

  const selected = () => form.querySelector<HTMLInputElement>("input[name=voz]:checked")!;
  const setState = (state: "idle" | "loading" | "playing") => (player.dataset.state = state);

  function updateCount() {
    count.textContent = `${text.value.length}/${text.maxLength}`;
  }

  function render() {
    const voice = selected();
    $("[data-player-name]").textContent = voice.dataset.name ?? "";
    $("[data-player-tags]").textContent = voice.dataset.tags ?? "";
    if (!edited) text.value = lines[voice.dataset.gender === "m" ? "m" : "f"].replace("{nombre}", voice.dataset.name ?? "");
    updateCount();
  }

  function updateProgress() {
    // Mientras se genera no se sabe cuanto dura: la barra espera y el total se muestra con puntos.
    const known = active ? active.final() : true;
    const total = active ? active.total() : (clip?.buffer.duration ?? 0);
    const elapsed = active ? Math.min(active.elapsed(), total) : 0;
    progress.style.width = `${known && total > 0 ? (elapsed / total) * 100 : 0}%`;
    time.textContent = `${clock(elapsed)} / ${known ? clock(total) : "…"}`;
    if (active) frame = requestAnimationFrame(updateProgress);
  }

  function stop() {
    request?.abort();
    request = null;
    const current = active;
    active = null;
    current?.stop();
    cancelAnimationFrame(frame);
    setState("idle");
    play.disabled = false;
    play.setAttribute("aria-label", "Reproducir");
    updateProgress();
  }

  function playing(handle: NonNullable<typeof active>, voice: string) {
    active = handle;
    setState("playing");
    play.disabled = false;
    track("voice_sample_play", { voice });
    play.setAttribute("aria-label", "Pausar");
    updateProgress();
  }

  /** Repite un audio ya generado: suena al instante. */
  function replay(ac: AudioContext, buffer: AudioBuffer, voice: string) {
    const source = ac.createBufferSource();
    source.buffer = buffer;
    source.connect(ac.destination);
    const startedAt = ac.currentTime;
    const handle = {
      elapsed: () => ac.currentTime - startedAt,
      total: () => buffer.duration,
      final: () => true,
      stop: () => {
        source.onended = null;
        source.stop();
      },
    };
    source.onended = () => {
      if (active === handle) stop();
    };
    source.start();
    playing(handle, voice);
  }

  /** Pide el audio y lo reproduce a medida que llega: suena a los ~0,5 s en vez de esperar la sintesis entera. */
  async function stream(ac: AudioContext, voice: string, content: string, key: string) {
    setState("loading");
    play.disabled = true;
    const controller = new AbortController();
    request = controller;
    try {
      const body = await synthesizeStream(voice, content, controller.signal);
      let playback!: PcmStreamPlayback;
      const handle = {
        elapsed: () => playback.elapsed(),
        total: () => playback.total(),
        final: () => playback.isFinal(),
        stop: () => playback.stop(),
      };
      playback = new PcmStreamPlayback(ac, body, {
        onStart: () => {
          if (request === controller) playing(handle, voice);
        },
        onEnd: () => {
          if (active === handle) stop();
        },
      });
      active = handle;
      const pcm = await playback.generated;
      if (!pcm) return; // se corto antes de terminar
      if (!pcm.length) throw new UserFacingError("No pudimos generar el audio. Probá de nuevo.");
      // Ya llego todo: queda guardado para repetirlo sin volver a generar.
      const buffer = ac.createBuffer(1, pcm.length >> 1, PCM_SAMPLE_RATE);
      buffer.getChannelData(0).set(int16ToFloat32(pcm));
      clip = { key, buffer };
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        error.textContent = err instanceof UserFacingError ? err.message : "No pudimos generar el audio. Probá de nuevo.";
      }
      if (request === controller) stop();
    } finally {
      if (request === controller) {
        request = null;
        play.disabled = false;
      }
    }
  }

  async function start() {
    const content = text.value.trim();
    if (!content) {
      error.textContent = "Escribí un texto para escuchar.";
      return;
    }
    error.textContent = "";
    context ??= new AudioContext();
    const ac = context;
    void ac.resume();
    const voice = selected().value;
    const key = `${voice}\n${content}`;
    if (clip?.key === key) replay(ac, clip.buffer, voice);
    else await stream(ac, voice, content, key);
  }

  play.addEventListener("click", () => (player.dataset.state === "playing" ? stop() : void start()));
  form.addEventListener("change", () => {
    stop();
    render();
  });
  text.addEventListener("input", () => {
    edited = text.value.trim().length > 0;
    error.textContent = "";
    updateCount();
  });
  more.addEventListener("click", () => {
    const open = form.toggleAttribute("data-all");
    more.textContent = open ? "Ver menos" : "Ver más voces";
    more.setAttribute("aria-expanded", String(open));
  });

  setState("idle");
  render();
  updateProgress();
}

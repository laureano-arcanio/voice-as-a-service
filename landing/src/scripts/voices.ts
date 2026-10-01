import { synthesize } from "./api";
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
  let node: AudioBufferSourceNode | null = null;
  let startedAt = 0;
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
    const total = clip?.buffer.duration ?? 0;
    const elapsed = node && context ? Math.min(context.currentTime - startedAt, total) : 0;
    progress.style.width = `${total > 0 ? (elapsed / total) * 100 : 0}%`;
    time.textContent = `${clock(elapsed)} / ${clock(total)}`;
    if (node) frame = requestAnimationFrame(updateProgress);
  }

  function stop() {
    request?.abort();
    request = null;
    const current = node;
    node = null;
    if (current) {
      current.onended = null;
      current.stop();
    }
    cancelAnimationFrame(frame);
    setState("idle");
    play.disabled = false;
    play.setAttribute("aria-label", "Reproducir");
    updateProgress();
  }

  async function load(voice: string, content: string, ac: AudioContext): Promise<AudioBuffer | null> {
    const key = `${voice}\n${content}`;
    if (clip?.key === key) return clip.buffer;
    setState("loading");
    play.disabled = true;
    request = new AbortController();
    try {
      const blob = await synthesize(voice, content, request.signal);
      const buffer = await ac.decodeAudioData(await blob.arrayBuffer());
      clip = { key, buffer };
      return buffer;
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        error.textContent = err instanceof UserFacingError ? err.message : "No pudimos generar el audio. Probá de nuevo.";
      }
      return null;
    } finally {
      request = null;
      play.disabled = false;
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
    const buffer = await load(selected().value, content, ac);
    if (!buffer) {
      stop();
      return;
    }
    const source = ac.createBufferSource();
    source.buffer = buffer;
    source.connect(ac.destination);
    source.onended = () => {
      if (node === source) stop();
    };
    node = source;
    startedAt = ac.currentTime;
    source.start();
    setState("playing");
    play.setAttribute("aria-label", "Pausar");
    updateProgress();
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

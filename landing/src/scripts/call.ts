import type { LocalAudioTrack, Room, TextStreamReader } from "livekit-client";
import { ApiError, callResult, type DemoCall, type DemoField, type DemoResult, startCall } from "./api";
import { track } from "./analytics";
import { UserFacingError } from "./errors";

type State = "idle" | "connecting" | "live" | "processing" | "result";
type Role = "assistant" | "user";

const STATUS: Record<State, string> = {
  idle: "listo",
  connecting: "conectando",
  live: "en llamada",
  processing: "procesando",
  result: "terminada",
};
const POLL_MS = 1000;
const POLL_TIMEOUT_MS = 45_000;

const livekit = () => import("livekit-client");
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function clock(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function display(field: DemoField): string | null {
  const value = field.value;
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "boolean") return value ? "Sí" : "No";
  const text = String(value);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function errorMessage(error: unknown): string {
  if (error instanceof UserFacingError) return error.message;
  return "No pudimos conectar la llamada. Probá de nuevo en un rato.";
}

export function initCallWidget(root: HTMLElement) {
  const $ = <T extends Element = HTMLElement>(selector: string) => root.querySelector<T>(selector)!;
  const form = $<HTMLFormElement>("[data-idle]");
  const statusText = $("[data-status-text]");
  const note = $("[data-note]");
  const noteHtml = note.innerHTML;
  const startButton = $<HTMLButtonElement>("[data-start]");
  const liveTitle = $("[data-live-title]");
  const liveHint = $("[data-live-hint]");
  const timer = $("[data-timer]");
  const transcript = $("[data-transcript]");
  const transcriptEmpty = $("[data-transcript-empty]");
  const muteButton = $<HTMLButtonElement>("[data-mute]");
  const muteLabel = $("[data-mute-label]");
  const unmuteAudio = $<HTMLButtonElement>("[data-unmute-audio]");
  const outcome = $("[data-outcome]");
  const duration = $("[data-duration]");
  const resultAgent = $("[data-result-agent]");
  const fields = $("[data-fields]");
  const fieldsTitle = $("[data-fields-title]");
  const fieldsEmpty = $("[data-fields-empty]");
  const resultTranscript = $("[data-result-transcript]");
  const fieldRow = $<HTMLTemplateElement>("[data-field-row]");
  const lineTemplate = $<HTMLTemplateElement>("[data-line]");

  let room: Room | null = null;
  let mic: LocalAudioTrack | null = null;
  let call: DemoCall | null = null;
  let ticker: number | undefined;
  let ending = false;
  const lines = new Map<string, HTMLElement>();

  const selected = () => form.querySelector<HTMLInputElement>("input[name=agente]:checked")!;

  function setState(state: State) {
    root.dataset.state = state;
    statusText.textContent = STATUS[state];
  }

  function warn(message: string) {
    note.textContent = message;
    note.dataset.warn = "";
  }

  function resetNote() {
    note.innerHTML = noteHtml;
    delete note.dataset.warn;
  }

  function line(container: HTMLElement, role: Role, text: string): HTMLElement {
    const el = lineTemplate.content.firstElementChild!.cloneNode(true) as HTMLElement;
    el.dataset.role = role;
    el.textContent = text;
    container.appendChild(el);
    return el;
  }

  function showLine(id: string, role: Role, text: string) {
    if (!text.trim()) return;
    transcriptEmpty.hidden = true;
    const existing = lines.get(id);
    if (existing) existing.textContent = text;
    else lines.set(id, line(transcript, role, text));
    transcript.scrollTop = transcript.scrollHeight;
  }

  async function onTranscription(reader: TextStreamReader, participant: { identity: string }) {
    const attributes = reader.info.attributes ?? {};
    const trackId = attributes["lk.transcribed_track_id"];
    const local = room?.localParticipant;
    const isUser =
      participant.identity === local?.identity || (trackId !== undefined && !!local?.trackPublications.has(trackId));
    const id = attributes["lk.segment_id"] ?? reader.info.id;
    let text = "";
    for await (const chunk of reader) {
      text += chunk;
      showLine(id, isUser ? "user" : "assistant", text);
    }
  }

  function releaseMedia() {
    window.clearInterval(ticker);
    mic?.stop();
    mic = null;
    root.querySelectorAll("audio").forEach((el) => el.remove());
    room?.removeAllListeners();
    room = null;
  }

  function renderResult(result: DemoResult) {
    const title = result.outcome?.label ?? (result.status === "fallida" ? "No se pudo completar" : "Sin terminar");
    outcome.textContent = title;
    if (result.outcome?.goal) outcome.dataset.goal = "";
    else delete outcome.dataset.goal;
    duration.textContent = `Duración ${clock(result.duration_seconds)}`;
    resultAgent.textContent = result.agent_name || liveTitle.textContent || "El agente";
    const taken = result.fields.flatMap((field) => {
      const value = display(field);
      return value === null ? [] : [{ label: field.label, value }];
    });
    fields.replaceChildren(
      ...taken.map(({ label, value }) => {
        const row = fieldRow.content.firstElementChild!.cloneNode(true) as HTMLElement;
        row.querySelector("dt")!.textContent = label;
        row.querySelector("dd")!.textContent = value;
        return row;
      }),
    );
    fields.hidden = fieldsTitle.hidden = taken.length === 0;
    fieldsEmpty.hidden = taken.length > 0;
    resultTranscript.replaceChildren();
    result.messages.forEach((m) => line(resultTranscript, m.role, m.text));
    setState("result");
  }

  async function finish() {
    if (ending) return;
    ending = true;
    releaseMedia();
    const current = call;
    if (!current) {
      setState("idle");
      return;
    }
    setState("processing");
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    let last: DemoResult | null = null;
    while (Date.now() < deadline) {
      try {
        last = await callResult(current);
        if (last.final) break;
      } catch (error) {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) break;
      }
      await sleep(POLL_MS);
    }
    if (last && (last.final || last.messages.length > 1)) {
      renderResult(last);
    } else {
      setState("idle");
      warn("La llamada terminó, pero no pudimos traer el resultado.");
    }
  }

  async function createRoom(): Promise<Room> {
    const { Room, RoomEvent, Track } = await livekit();
    const r = new Room();
    r.on(RoomEvent.TrackSubscribed, (track) => {
      if (track.kind !== Track.Kind.Audio) return;
      const el = track.attach();
      el.hidden = true;
      root.appendChild(el);
    });
    r.on(RoomEvent.TrackUnsubscribed, (track) => track.detach().forEach((el) => el.remove()));
    r.on(RoomEvent.AudioPlaybackStatusChanged, () => unmuteAudio.classList.toggle("hidden", r.canPlaybackAudio));
    r.on(RoomEvent.Disconnected, () => void finish());
    r.registerTextStreamHandler("lk.transcription", (reader, participant) => void onTranscription(reader, participant));
    return r;
  }

  form.addEventListener("change", () => {
    resetNote();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (root.dataset.state !== "idle") return;
    const agent = selected();
    resetNote();
    startButton.blur();
    liveTitle.textContent = agent.dataset.title ?? "";
    liveHint.textContent = "Conectando con el agente…";
    timer.textContent = "0:00";
    lines.clear();
    transcript.replaceChildren(transcriptEmpty);
    transcriptEmpty.hidden = false;
    muteButton.disabled = true;
    muteButton.setAttribute("aria-pressed", "false");
    muteLabel.textContent = "Silenciar";
    ending = false;
    call = null;
    setState("connecting");

    try {
      const { createLocalAudioTrack } = await livekit();
      mic = await createLocalAudioTrack({ echoCancellation: true, noiseSuppression: true, autoGainControl: true });
    } catch {
      releaseMedia();
      setState("idle");
      warn("Necesitamos permiso para usar el micrófono. Habilitalo en el navegador y volvé a intentar.");
      return;
    }

    try {
      call = await startCall(agent.value);
      room = await createRoom();
      await room.connect(call.livekit_url, call.token);
      await room.localParticipant.publishTrack(mic);
      await room.startAudio().catch(() => undefined);
      unmuteAudio.classList.toggle("hidden", room.canPlaybackAudio);
    } catch (error) {
      const failed = call;
      call = null;
      ending = true;
      await room?.disconnect();
      releaseMedia();
      setState("idle");
      warn(errorMessage(error));
      if (failed) console.warn("demo call failed", failed.conversation_id, error);
      return;
    }

    const limit = call.max_duration_seconds;
    const started = Date.now();
    muteButton.disabled = false;
    liveHint.textContent = `En llamada · máximo ${Math.round(limit / 60)} min`;
    setState("live");
    track("demo_call_start", { agent: agent.value, page: location.pathname });
    ticker = window.setInterval(() => {
      timer.textContent = clock((Date.now() - started) / 1000);
    }, 500);
  });

  $<HTMLButtonElement>("[data-hangup]").addEventListener("click", () => {
    if (room) void room.disconnect();
    else void finish();
  });

  muteButton.addEventListener("click", async () => {
    if (!mic) return;
    const muted = !mic.isMuted;
    await (muted ? mic.mute() : mic.unmute());
    muteButton.setAttribute("aria-pressed", String(muted));
    muteLabel.textContent = muted ? "Activar" : "Silenciar";
  });

  unmuteAudio.addEventListener("click", async () => {
    await room?.startAudio();
    unmuteAudio.classList.toggle("hidden", !!room?.canPlaybackAudio);
  });

  $<HTMLButtonElement>("[data-again]").addEventListener("click", () => {
    call = null;
    ending = false;
    resetNote();
    setState("idle");
  });

  window.addEventListener("pagehide", () => void room?.disconnect());
}

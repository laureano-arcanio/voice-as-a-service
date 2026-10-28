// Pagina publica del link para llamar a un agente (docs/features/LINK_LLAMADA.md): una pantalla
// de llamada telefonica. Los datos del link vienen en #link-data (app/api/call_link_host.py) y la
// llamada arranca con POST /api/v1/public/call-links/{token}/calls.
import '@fontsource-variable/figtree';
import '@fontsource-variable/bricolage-grotesque';
import '@fontsource/ibm-plex-mono/latin-400.css';
import './llamar.css';
import type { LocalAudioTrack, Participant, Room, TextStreamReader } from 'livekit-client';
import { initials } from '@/lib/initials';
import { CaptchaError, loadTurnstile, turnstileToken } from './turnstile';

interface LinkData {
  found: boolean;
  token?: string;
  display_name?: string;
  company_name?: string;
  subtitle?: string;
  image_url?: string | null;
  max_call_seconds?: number;
  records_audio?: boolean;
  available?: boolean;
  turnstile_site_key?: string;
  home_url?: string;
}

interface CallOut {
  livekit_url: string;
  token: string;
  max_call_seconds: number;
}

type State = 'loading' | 'idle' | 'connecting' | 'live' | 'ended' | 'error';
type Group = 'idle' | 'call' | 'retry' | null;

const WARN_BEFORE_END_S = 30;
const RECONNECT_GIVE_UP_MS = 15_000;
const IN_APP = /Instagram|FBAN|FBAV|FB_IAB|FBIOS|Line\/|TikTok|musical_ly|Snapchat/i;

const livekit = () => import('livekit-client');
const $ = <T extends HTMLElement = HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

const data: LinkData = JSON.parse(document.getElementById('link-data')?.textContent || '{"found":false}');
const phone = $('.phone');
const status = $('[data-status]');
const timer = $('[data-timer]');
const hint = $('[data-hint]');
const notice = $('[data-notice]');
const noticeTitle = $('[data-notice-title]');
const noticeText = $('[data-notice-text]');
const noticeSteps = $<HTMLOListElement>('[data-notice-steps]');
const captionsToggle = $<HTMLButtonElement>('[data-captions-toggle]');
const captions = $('[data-captions]');
const muteButton = $<HTMLButtonElement>('[data-mute]');
const muteLabel = $('[data-mute-label]');
const unmuteAudio = $<HTMLButtonElement>('[data-unmute-audio]');
const retryButton = $<HTMLButtonElement>('[data-retry]');
const agentName = data.display_name ?? '';
const maxSeconds = data.max_call_seconds ?? 300;

let room: Room | null = null;
let mic: LocalAudioTrack | null = null;
let startedAt = 0;
let ticker: number | undefined;
let levelFrame: number | undefined;
let reconnectTimer: number | undefined;
let wakeLock: WakeLockSentinel | null = null;
let ending = false;
let endReason: 'hangup' | 'limit' | 'lost' | null = null;
const lines = new Map<string, HTMLParagraphElement>();

// ---------- presentacion ----------

function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

function setState(state: State, group: Group, statusText: string) {
  phone.dataset.state = state;
  status.textContent = statusText;
  document.querySelectorAll<HTMLElement>('[data-group]').forEach((el) => {
    el.hidden = el.dataset.group !== group;
  });
  timer.hidden = !(state === 'live' || state === 'ended');
  captionsToggle.hidden = state !== 'live' && !(state === 'ended' && lines.size > 0);
  if (state !== 'live' && state !== 'ended') {
    captions.hidden = true;
    captionsToggle.setAttribute('aria-expanded', 'false');
    captionsToggle.textContent = 'Ver subtítulos';
  }
  if (state !== 'error') notice.hidden = true;
}

function showNotice(title: string, text: string, steps: string[] = []) {
  noticeTitle.textContent = title;
  noticeText.textContent = text;
  noticeSteps.replaceChildren(
    ...steps.map((s) => {
      const li = document.createElement('li');
      li.textContent = s;
      return li;
    }),
  );
  noticeSteps.hidden = steps.length === 0;
  notice.hidden = false;
}

/** Error que corta: el texto en el aviso y, si se puede, "Volver a intentar". */
function fail(title: string, text: string, { retry = true, steps = [] as string[] } = {}) {
  setState('error', retry ? 'retry' : null, '');
  hint.textContent = '';
  retryButton.textContent = 'Volver a intentar';
  showNotice(title, text, steps);
  retryButton.focus();
}

function idle() {
  hint.textContent = '';
  setState('idle', 'idle', 'Disponible');
  if (IN_APP.test(navigator.userAgent)) {
    showNotice(
      'Abrí este link en el navegador',
      'Desde esta app el micrófono puede no funcionar. Tocá los tres puntos y elegí "Abrir en el navegador".',
    );
    notice.hidden = false;
  }
}

function micSteps(): string[] {
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
  return ios
    ? [
        'Tocá "aA" en la barra de direcciones.',
        'Configuración del sitio → Micrófono → Permitir.',
        'Volvé a intentar.',
      ]
    : ['Tocá el candado de la barra de direcciones.', 'Micrófono → Permitir.', 'Volvé a intentar.'];
}

// ---------- subtitulos ----------

function showLine(id: string, isUser: boolean, text: string) {
  if (!text.trim()) return;
  let line = lines.get(id);
  if (!line) {
    line = document.createElement('p');
    const who = document.createElement('b');
    who.textContent = isUser ? 'Vos: ' : `${agentName}: `;
    line.append(who, document.createTextNode(''));
    lines.set(id, line);
    captions.appendChild(line);
  }
  line.lastChild!.textContent = text;
  captions.scrollTop = captions.scrollHeight;
}

async function onTranscription(reader: TextStreamReader, participant: { identity: string }) {
  const attributes = reader.info.attributes ?? {};
  const trackId = attributes['lk.transcribed_track_id'];
  const local = room?.localParticipant;
  const isUser =
    participant.identity === local?.identity ||
    (trackId !== undefined && !!local?.trackPublications.has(trackId));
  const id = attributes['lk.segment_id'] ?? reader.info.id;
  let text = '';
  for await (const chunk of reader) {
    text += chunk;
    showLine(id, isUser, text);
  }
}

captionsToggle.addEventListener('click', () => {
  const open = captions.hidden;
  captions.hidden = !open;
  captionsToggle.setAttribute('aria-expanded', String(open));
  captionsToggle.textContent = open ? 'Ocultar subtítulos' : 'Ver subtítulos';
});

// ---------- llamada ----------

async function keepAwake() {
  try {
    wakeLock = (await navigator.wakeLock?.request('screen')) ?? null;
  } catch {
    wakeLock = null;
  }
}

function trackLevel() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const loop = () => {
    const participant = [...(room?.remoteParticipants.values() ?? [])][0];
    const level = reduce ? 0 : Math.min(1, (participant?.audioLevel ?? 0) * 3);
    phone.style.setProperty('--level', level.toFixed(3));
    levelFrame = requestAnimationFrame(loop);
  };
  levelFrame = requestAnimationFrame(loop);
}

function goLive() {
  if (phone.dataset.state === 'live') return;
  startedAt = Date.now();
  setState('live', 'call', 'En llamada');
  hint.textContent = `${agentName} habla…`;
  muteButton.disabled = false;
  trackLevel();
  void keepAwake();
  ticker = window.setInterval(() => {
    const elapsed = (Date.now() - startedAt) / 1000;
    timer.textContent = clock(elapsed);
    if (maxSeconds - elapsed <= WARN_BEFORE_END_S && maxSeconds - elapsed > 0) {
      hint.textContent = 'Queda medio minuto de llamada.';
    }
  }, 500);
}

function release() {
  window.clearInterval(ticker);
  window.clearTimeout(reconnectTimer);
  if (levelFrame) cancelAnimationFrame(levelFrame);
  phone.style.setProperty('--level', '0');
  mic?.stop();
  mic = null;
  document.querySelectorAll('audio').forEach((el) => el.remove());
  room?.removeAllListeners();
  room = null;
  void wakeLock?.release().catch(() => undefined);
  wakeLock = null;
  unmuteAudio.hidden = true;
  muteButton.disabled = true;
  muteButton.setAttribute('aria-pressed', 'false');
  muteLabel.textContent = 'Silenciar';
  $('[data-mic-on]').hidden = false;
  $('[data-mic-off]').hidden = true;
}

function finish() {
  if (ending) return;
  ending = true;
  const wasLive = phone.dataset.state === 'live';
  const elapsed = startedAt ? (Date.now() - startedAt) / 1000 : 0;
  release();
  if (!wasLive) {
    fail('No pudimos conectar la llamada', 'Probá de nuevo en unos segundos.');
    return;
  }
  timer.textContent = clock(elapsed);
  setState('ended', 'retry', 'Llamada finalizada');
  retryButton.textContent = 'Volver a llamar';
  hint.textContent =
    endReason === 'lost'
      ? 'Se cortó la conexión.'
      : elapsed >= maxSeconds - 2
        ? 'Se alcanzó el tiempo máximo de la llamada.'
        : '';
  retryButton.focus();
}

async function createRoom(): Promise<Room> {
  const { Room, RoomEvent, Track } = await livekit();
  const r = new Room({ adaptiveStream: false, dynacast: false });
  r.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind !== Track.Kind.Audio) return;
    const el = track.attach();
    el.hidden = true;
    document.body.appendChild(el);
    goLive();
  });
  r.on(RoomEvent.TrackUnsubscribed, (track) => track.detach().forEach((el) => el.remove()));
  r.on(RoomEvent.AudioPlaybackStatusChanged, () => {
    unmuteAudio.hidden = r.canPlaybackAudio;
  });
  r.on(RoomEvent.ActiveSpeakersChanged, (speakers: Participant[]) => {
    if (phone.dataset.state !== 'live' || hint.textContent?.startsWith('Queda')) return;
    const local = r.localParticipant.identity;
    const agentSpeaks = speakers.some((p) => p.identity !== local);
    const userSpeaks = speakers.some((p) => p.identity === local);
    hint.textContent = agentSpeaks ? `${agentName} habla…` : userSpeaks ? 'Te escucha…' : '';
  });
  r.on(RoomEvent.Reconnecting, () => {
    hint.textContent = 'Reconectando…';
    reconnectTimer = window.setTimeout(() => {
      endReason = 'lost';
      void r.disconnect();
    }, RECONNECT_GIVE_UP_MS);
  });
  r.on(RoomEvent.Reconnected, () => {
    window.clearTimeout(reconnectTimer);
    hint.textContent = '';
  });
  r.on(RoomEvent.Disconnected, () => finish());
  r.registerTextStreamHandler(
    'lk.transcription',
    (reader, participant) => void onTranscription(reader, participant),
  );
  return r;
}

async function requestCall(captcha: string): Promise<CallOut> {
  let r: Response;
  try {
    r = await fetch(`/api/v1/public/call-links/${encodeURIComponent(data.token!)}/calls`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ turnstile_token: captcha }),
    });
  } catch {
    throw new CallError('network');
  }
  if (r.ok) return (await r.json()) as CallOut;
  const body = (await r.json().catch(() => ({}))) as { code?: string; detail?: string };
  throw new CallError(body.code ?? `http_${r.status}`, body.detail);
}

class CallError extends Error {
  constructor(
    readonly code: string,
    readonly detail?: string,
  ) {
    super(code);
  }
}

function callFailed(error: unknown) {
  if (error instanceof CaptchaError) return fail('No pudimos verificar la llamada', error.message);
  const code = error instanceof CallError ? error.code : 'unknown';
  switch (code) {
    case 'busy':
      return fail('Todas las líneas están ocupadas', 'Probá en unos minutos.');
    case 'rate_limited':
      return fail('Hiciste varias llamadas seguidas', 'Probá más tarde.', { retry: false });
    case 'unavailable':
      return fail('No disponible', 'Este canal no está disponible en este momento.', { retry: false });
    case 'link_not_found':
    case 'http_404':
      return fail('Este link ya no está activo', 'Pedile el link nuevo a quien te lo compartió.', {
        retry: false,
      });
    case 'captcha_failed':
      return fail('No pudimos verificar la llamada', 'Recargá la página y volvé a intentar.');
    default:
      return fail('No pudimos conectar la llamada', 'Revisá tu conexión y volvé a intentar.');
  }
}

async function call() {
  if (!['idle', 'error', 'ended'].includes(phone.dataset.state ?? '')) return;
  if (!navigator.mediaDevices?.getUserMedia || !('RTCPeerConnection' in window)) {
    fail('Este navegador no puede llamar', 'Abrí este link en Chrome, Safari o Firefox.', { retry: false });
    return;
  }
  ending = false;
  endReason = null;
  startedAt = 0;
  lines.clear();
  captions.replaceChildren();
  timer.textContent = clock(0);
  hint.textContent = '';
  setState('connecting', 'call', 'Llamando…');

  // 1. Microfono, con el gesto del usuario: si lo niega, no se gasta la llamada.
  const { createLocalAudioTrack } = await livekit();
  try {
    mic = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    });
  } catch (error) {
    release();
    const name = error instanceof DOMException ? error.name : '';
    if (name === 'NotFoundError' || name === 'OverconstrainedError') {
      fail('No encontramos un micrófono', 'Conectá uno y volvé a intentar.');
    } else {
      fail(`Sin permiso para el micrófono`, `Para hablar con ${agentName}, permitilo:`, {
        steps: micSteps(),
      });
    }
    return;
  }

  // 2. Turnstile y la llamada; 3. la room.
  try {
    const started = await requestCall(await turnstileToken(data.turnstile_site_key!));
    room = await createRoom();
    await room.connect(started.livekit_url, started.token);
    await room.localParticipant.publishTrack(mic);
    await room.startAudio().catch(() => undefined);
    unmuteAudio.hidden = room.canPlaybackAudio;
  } catch (error) {
    ending = true;
    await room?.disconnect();
    release();
    callFailed(error);
  }
}

$<HTMLButtonElement>('[data-call]').addEventListener('click', () => void call());
retryButton.addEventListener('click', () => void call());

$<HTMLButtonElement>('[data-hangup]').addEventListener('click', () => {
  endReason = 'hangup';
  if (room) void room.disconnect();
  else finish();
});

muteButton.addEventListener('click', async () => {
  if (!mic) return;
  const muted = !mic.isMuted;
  await (muted ? mic.mute() : mic.unmute());
  muteButton.setAttribute('aria-pressed', String(muted));
  muteLabel.textContent = muted ? 'Activar' : 'Silenciar';
  $('[data-mic-on]').hidden = muted;
  $('[data-mic-off]').hidden = !muted;
});

unmuteAudio.addEventListener('click', async () => {
  await room?.startAudio();
  unmuteAudio.hidden = !!room?.canPlaybackAudio;
});

window.addEventListener('beforeunload', (event) => {
  if (phone.dataset.state === 'live' || phone.dataset.state === 'connecting') event.preventDefault();
});
window.addEventListener('pagehide', () => void room?.disconnect());
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && phone.dataset.state === 'live' && !wakeLock) void keepAwake();
});

// ---------- arranque ----------

/** Logo o foto del link en el circulo; si no carga, queda la inicial. */
function showImage(src: string) {
  const avatar = $('.avatar');
  const img = document.createElement('img');
  img.alt = '';
  img.src = src;
  img.addEventListener('load', () => avatar.classList.add('has-image'));
  img.addEventListener('error', () => img.remove());
  avatar.append(img);
}

function init() {
  const company = data.company_name ?? '';
  $('[data-initials]').textContent = data.found ? initials(company) : '·';
  if (data.found && data.image_url) showImage(data.image_url);
  const name = $('[data-name]');
  name.textContent = data.found ? agentName : 'Link no disponible';
  // "Gaby, asistente de" y abajo la empresa: se lee como una frase.
  if (data.found && company) {
    const role = document.createElement('span');
    role.className = 'role';
    role.textContent = ', asistente de';
    name.append(role);
  }
  $('[data-company]').textContent = company;
  const subtitle = $('[data-subtitle]');
  subtitle.textContent = data.subtitle ?? '';
  subtitle.hidden = !data.subtitle;
  const home = data.home_url ?? 'https://atentina.com.ar';
  $<HTMLAnchorElement>('[data-home]').href = home;
  $<HTMLAnchorElement>('[data-privacy]').href = `${home}/privacidad`;

  if (!data.found) {
    fail('Este link ya no está activo', 'Pedile el link nuevo a quien te lo compartió.', { retry: false });
    return;
  }
  const minutes = Math.max(1, Math.round(maxSeconds / 60));
  $('[data-note]').textContent =
    `Usa el micrófono de tu dispositivo. La llamada dura hasta ${minutes} ${minutes === 1 ? 'minuto' : 'minutos'}.` +
    (data.records_audio ? ' La llamada se graba.' : '');
  if (!data.available) {
    fail('No disponible', 'Este canal no está disponible en este momento.', { retry: false });
    status.textContent = 'No disponible';
    return;
  }
  idle();
  // Precarga: que al tocar "Llamar" no haya que esperar el SDK ni el script de Turnstile.
  void livekit();
  void loadTurnstile().catch(() => undefined);
}

init();

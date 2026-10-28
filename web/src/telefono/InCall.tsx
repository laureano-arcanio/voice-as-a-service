// Pantallas de llamada del teléfono: la llamada (saliente o atendida, hasta que termina) y la entrante que suena.
// Todo el estado es del CallProvider, el mismo del teléfono del panel.
import { Text } from '@mantine/core';
import {
  IconDialpad,
  IconMicrophone,
  IconMicrophoneOff,
  IconPhone,
  IconPhoneOff,
  IconTextCaption,
  IconUserPlus,
  IconVolume,
} from '@tabler/icons-react';
import { type ReactNode, useEffect, useRef, useState } from 'react';
import { SaveContactModal } from '@/features/phone/CallBar';
import { type CallPhase, type CallResult, useDirectCall, usePresence } from '@/features/phone/context';
import type { Ringing } from '@/features/phone/types';
import { formatDuration } from '@/lib/format';
import { Keypad } from './Keypad';
import { TONE_KEYS } from './keys';
import { Avatar } from './parts';

const PHASE_LABEL: Partial<Record<CallPhase, string>> = {
  mic: 'Conectando el micrófono…',
  connecting: 'Conectando…',
  dialing: 'Llamando…',
  ringing: 'Sonando…',
};

const RESULT_LABEL: Record<CallResult, string> = {
  completed: 'Llamada terminada',
  no_answer: 'No atendió',
  busy: 'Ocupado',
  failed: 'No se pudo completar',
  hangup: 'Cortaste la llamada',
};

/** Una terminada sin nada que hacer (con contacto y bien) se cierra sola, como en el celular. */
const AUTO_CLOSE_MS = 4000;

function Timer({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return <span aria-label="Duración">{formatDuration(Math.max(1, (now - since) / 1000))}</span>;
}

function Control({
  label,
  icon,
  active,
  disabled,
  onClick,
}: {
  label: string;
  icon: ReactNode;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="tel-control"
      data-active={active || undefined}
      aria-pressed={active ?? undefined}
      disabled={disabled}
      onClick={onClick}
    >
      <span className="tel-control-icon">{icon}</span>
      <span className="tel-control-label">{label}</span>
    </button>
  );
}

function Captions() {
  const { transcript } = useDirectCall();
  const end = useRef<HTMLDivElement | null>(null);
  useEffect(() => end.current?.scrollIntoView?.({ block: 'end' }), [transcript.length]);
  return (
    <div className="tel-captions" aria-label="Subtítulos de la llamada" aria-live="polite">
      {transcript.length === 0 ? (
        <p className="tel-muted">Los subtítulos aparecen cuando alguien habla.</p>
      ) : (
        transcript.map((l) => (
          <p key={l.id} data-mine={l.mine || undefined}>
            <b>{l.who}:</b> {l.text}
          </p>
        ))
      )}
      <div ref={end} />
    </div>
  );
}

/** La llamada: desde que se pide el micrófono hasta que termina (o no pudo empezar). */
export function InCallScreen({ onRedial }: { onRedial: () => void }) {
  const c = useDirectCall();
  const [panel, setPanel] = useState<'none' | 'keypad' | 'captions'>('none');
  const [tones, setTones] = useState('');
  const [saving, setSaving] = useState(false);
  const live = c.busy;
  const active = c.phase === 'active';
  const t = c.target;
  const name = t?.name || t?.phone || (c.direction === 'inbound' ? 'Llamada entrante' : 'Llamada');
  const line = t?.fromLabel ? (c.direction === 'inbound' ? `Entrante por ${t.fromLabel}` : `Desde ${t.fromLabel}`) : '';

  const canClose = c.phase === 'ended' && c.result === 'completed' && !!t?.contactId && !saving;
  useEffect(() => {
    if (!canClose) return;
    const timer = window.setTimeout(c.dismiss, AUTO_CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [canClose, c.dismiss]);

  let status: ReactNode;
  if (c.phase === 'error') status = c.error?.title ?? 'No se pudo llamar';
  else if (c.phase === 'ended') status = RESULT_LABEL[c.result ?? 'completed'];
  else if (active && c.startedAt) status = <Timer since={c.startedAt} />;
  else status = PHASE_LABEL[c.phase] ?? '';

  return (
    <div className="tel-call" role="dialog" aria-label="Llamada" data-phase={c.phase}>
      <div className="tel-call-top">
        {line && <p className="tel-call-line">{line}</p>}
        <Avatar name={t?.name} size="xl" />
        <h1 className="tel-call-name">{name}</h1>
        {t?.name && t.phone && <p className="tel-call-phone mono">{t.phone}</p>}
        <p className="tel-call-status" role="status">
          {status}
        </p>
        {c.phase === 'error' && c.error?.message && <p className="tel-call-error">{c.error.message}</p>}
      </div>

      <div className="tel-call-middle">
        {live && panel === 'keypad' && (
          <>
            <p className="tel-tones mono" aria-label="Tonos marcados">
              {tones || ' '}
            </p>
            <Keypad
              keys={TONE_KEYS}
              disabled={!active}
              onKey={(k) => {
                setTones((s) => (s + k).slice(-24));
                c.dtmf(k);
              }}
            />
          </>
        )}
        {live && panel === 'captions' && <Captions />}
      </div>

      {live ? (
        <div className="tel-call-bottom">
          {c.audioBlocked && (
            <button type="button" className="tel-pill" onClick={c.startAudio}>
              <IconVolume size={18} /> Activar el sonido
            </button>
          )}
          <div className="tel-controls">
            <Control
              label={c.muted ? 'Activar micrófono' : 'Silenciar'}
              icon={c.muted ? <IconMicrophoneOff size={26} /> : <IconMicrophone size={26} />}
              active={c.muted}
              disabled={c.phase === 'mic' || c.phase === 'connecting'}
              onClick={c.toggleMute}
            />
            <Control
              label="Teclado"
              icon={<IconDialpad size={26} />}
              active={panel === 'keypad'}
              onClick={() => setPanel((p) => (p === 'keypad' ? 'none' : 'keypad'))}
            />
            <Control
              label="Subtítulos"
              icon={<IconTextCaption size={26} />}
              active={panel === 'captions'}
              onClick={() => setPanel((p) => (p === 'captions' ? 'none' : 'captions'))}
            />
          </div>
          <button type="button" className="tel-round tel-hangup" aria-label="Cortar" onClick={c.hangup}>
            <IconPhoneOff size={30} />
          </button>
        </div>
      ) : (
        <div className="tel-call-bottom">
          <div className="tel-controls">
            {c.direction === 'outbound' && t?.phone && (
              <Control label="Volver a llamar" icon={<IconPhone size={26} />} onClick={onRedial} />
            )}
            {t?.phone && !t.contactId && (
              <Control
                label="Guardar contacto"
                icon={<IconUserPlus size={26} />}
                onClick={() => setSaving(true)}
              />
            )}
          </div>
          <button type="button" className="tel-pill tel-pill-strong" onClick={c.dismiss}>
            Cerrar
          </button>
        </div>
      )}
      {saving && t?.phone && <SaveContactModal phone={t.phone} onClose={() => setSaving(false)} />}
    </div>
  );
}

/** Una entrante que suena (Disponible): atender o rechazar. Si no pudo atender (el micrófono), dice por qué. */
export function IncomingScreen({ ring, more }: { ring: Ringing; more: number }) {
  const c = useDirectCall();
  const { decline } = usePresence();
  const [answering, setAnswering] = useState(false);
  const line = ring.number_label || ring.number_e164;
  const failed = c.phase === 'error' && c.failedRingId === ring.conversation_id ? c.error : null;
  return (
    <div className="tel-call tel-incoming" role="dialog" aria-label="Llamada entrante">
      <div className="tel-call-top">
        <p className="tel-call-line">{line ? `Llamada entrante a ${line}` : 'Llamada entrante'}</p>
        <Avatar name={ring.contact_name} size="xl" ringing />
        <h1 className="tel-call-name">{ring.contact_name || ring.phone || 'Número privado'}</h1>
        {ring.contact_name && ring.phone && <p className="tel-call-phone mono">{ring.phone}</p>}
        {more > 0 && <p className="tel-call-status">{more} más sonando</p>}
        {failed && (
          <>
            <p className="tel-call-status" role="alert">
              {failed.title}
            </p>
            {failed.message && <p className="tel-call-error">{failed.message}</p>}
          </>
        )}
      </div>
      <div className="tel-call-middle" />
      <div className="tel-incoming-actions">
        <div className="tel-action">
          <button
            type="button"
            className="tel-round tel-hangup"
            aria-label="Rechazar"
            disabled={answering}
            onClick={() => decline(ring)}
          >
            <IconPhoneOff size={30} />
          </button>
          <Text size="sm">Rechazar</Text>
        </div>
        <div className="tel-action">
          <button
            type="button"
            className="tel-round tel-answer"
            aria-label="Atender"
            disabled={answering || !!c.disabledReason}
            onClick={() => {
              setAnswering(true);
              void c.answer(ring).finally(() => setAnswering(false));
            }}
          >
            <IconPhone size={30} />
          </button>
          <Text size="sm">Atender</Text>
        </div>
      </div>
    </div>
  );
}

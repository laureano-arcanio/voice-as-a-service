import { useCallback, useEffect, useRef, useState } from 'react';
import type { WaConfig } from '@/api/types';
import {
  type FacebookSdk,
  isFacebookOrigin,
  loadFacebookSdk,
  parseSignupMessage,
  type SignupEvent,
} from './facebook';

/** Lo que hace falta para POST /whatsapp/signup. */
export interface SignupResult {
  code: string;
  event: SignupEvent;
  waba_id: string;
  phone_number_id: string;
  business_id: string | null;
}

export class SignupAbort extends Error {
  readonly kind: 'cancel' | 'error' | 'timeout';
  constructor(kind: 'cancel' | 'error' | 'timeout', message: string) {
    super(message);
    this.name = 'SignupAbort';
    this.kind = kind;
  }
}

/** Espera por el evento FINISH despues del codigo (o al reves). El codigo vence a los 30 s. */
export const PAIR_TIMEOUT_MS = 10_000;
/** Sin codigo (popup cerrado): margen para que llegue el CANCEL con el paso. */
const CLOSE_GRACE_MS = 1_500;

/**
 * Embedded Signup v4: carga el SDK con la config de la API, y `launch()` abre el popup
 * y junta el codigo de FB.login con el mensaje WA_EMBEDDED_SIGNUP (waba_id y
 * phone_number_id). Llamar a launch() dentro del click: si no, el navegador bloquea el popup.
 */
export function useEmbeddedSignup(config: WaConfig | undefined) {
  const [sdk, setSdk] = useState<FacebookSdk | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const appId = config?.enabled ? config.app_id : null;
  const version = config?.graph_version ?? '';
  const locale = config?.sdk_locale ?? 'es_LA';

  useEffect(() => {
    if (!appId) return;
    let alive = true;
    loadFacebookSdk(appId, version, locale).then(
      (fb) => alive && setSdk(fb),
      (e: unknown) =>
        alive && setLoadError(e instanceof Error ? e.message : 'No se pudo cargar el SDK de Facebook.'),
    );
    return () => {
      alive = false;
    };
  }, [appId, version, locale]);

  // Al desmontar, deja de escuchar un alta en curso.
  useEffect(() => () => cleanupRef.current?.(), []);

  const launch = useCallback((): Promise<SignupResult> => {
    const configId = config?.config_id;
    if (!sdk || !configId)
      return Promise.reject(new SignupAbort('error', 'El alta de WhatsApp no está lista.'));
    cleanupRef.current?.();
    return new Promise<SignupResult>((resolve, reject) => {
      let code: string | null = null;
      let info: Omit<SignupResult, 'code'> | null = null;
      let timer: ReturnType<typeof setTimeout> | undefined;
      let done = false;

      const cleanup = () => {
        done = true;
        window.removeEventListener('message', onMessage);
        clearTimeout(timer);
        if (cleanupRef.current === cleanup) cleanupRef.current = null;
      };
      const fail = (e: SignupAbort) => {
        if (done) return;
        cleanup();
        reject(e);
      };
      const tryFinish = () => {
        if (done || !code || !info) return;
        cleanup();
        resolve({ code, ...info });
      };
      const waitForPair = () => {
        clearTimeout(timer);
        timer = setTimeout(
          () =>
            fail(new SignupAbort('timeout', 'Meta no devolvió todos los datos del alta. Probá de nuevo.')),
          PAIR_TIMEOUT_MS,
        );
      };

      function onMessage(ev: MessageEvent) {
        if (done || !isFacebookOrigin(ev.origin)) return;
        const msg = parseSignupMessage(ev.data);
        if (!msg) return;
        if (msg.kind === 'finish') {
          info = {
            event: msg.event,
            waba_id: msg.waba_id,
            phone_number_id: msg.phone_number_id,
            business_id: msg.business_id,
          };
          if (code) tryFinish();
          else waitForPair();
        } else if (msg.kind === 'cancel') {
          const step = msg.step ? ` (paso: ${msg.step})` : '';
          fail(new SignupAbort('cancel', `Se canceló el alta en Meta${step}.`));
        } else if (msg.kind === 'error') {
          const ref = msg.sessionId ? ` Sesión de Meta: ${msg.sessionId}.` : '';
          fail(new SignupAbort('error', `Meta informó un error: ${msg.message}.${ref}`));
        } else {
          fail(new SignupAbort('error', `Tipo de alta no soportado (${msg.event || 'desconocido'}).`));
        }
      }

      cleanupRef.current = cleanup;
      window.addEventListener('message', onMessage);
      try {
        // El callback no puede ser async (el SDK lo rechaza).
        sdk.login(
          (response) => {
            const c = response.authResponse?.code;
            if (!c) {
              // Popup cerrado: si llega el CANCEL con el paso, gana ese mensaje.
              clearTimeout(timer);
              timer = setTimeout(
                () => fail(new SignupAbort('cancel', 'Se cerró la ventana de Meta sin terminar el alta.')),
                CLOSE_GRACE_MS,
              );
              return;
            }
            code = c;
            if (info) tryFinish();
            else waitForPair();
          },
          {
            config_id: configId,
            response_type: 'code',
            override_default_response_type: true,
            extras: { setup: {} },
          },
        );
      } catch (e) {
        fail(
          new SignupAbort('error', e instanceof Error ? e.message : 'No se pudo abrir la ventana de Meta.'),
        );
      }
    });
  }, [sdk, config?.config_id]);

  return { ready: !!sdk, loadError, launch };
}

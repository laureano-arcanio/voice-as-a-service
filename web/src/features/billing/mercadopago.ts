// Formulario de tarjeta con los campos seguros de Mercado Pago (SDK v2, "Core Methods"): numero, vencimiento y
// codigo de seguridad son iframes de MP y la tarjeta vuelve tokenizada (card_token_id). Se carga solo en
// /plan/pagar, la unica pagina cuya CSP lo permite (app/api/http.py, MP_PAGES).
//
// No se usa el Card Payment Brick: para las tarjetas en las que MP marca el codigo de seguridad como opcional
// (Mastercard, Mastercard Prepaid como la de Mercado Pago, Naranja) el Brick no lo pide, y una suscripcion
// rechaza ese token ("Card token was generated without cvv validation", 10-oct-2026). Aca siempre se pide.
// Misma logica que landing/src/scripts/mercadopago.ts.

const SDK_URL = 'https://sdk.mercadopago.com/js/v2';

export type FieldName = 'cardNumber' | 'expirationDate' | 'securityCode';

interface Field {
  mount: (containerId: string) => Field;
  unmount: () => void;
  update: (options: Record<string, unknown>) => void;
  on: (event: string, cb: (payload: never) => void) => void;
}

interface MercadoPagoInstance {
  fields: {
    create: (type: FieldName, options: Record<string, unknown>) => Field;
    createCardToken: (data: {
      cardholderName: string;
      identificationType: string;
      identificationNumber: string;
    }) => Promise<{ id: string }>;
  };
  getIdentificationTypes: () => Promise<{ id: string; name: string }[]>;
  getPaymentMethods: (args: {
    bin: string;
  }) => Promise<{ results: { settings?: { security_code?: { length?: number } }[] }[] }>;
}

declare global {
  interface Window {
    MercadoPago?: new (publicKey: string, options?: { locale?: string }) => MercadoPagoInstance;
  }
}

let loading: Promise<void> | null = null;

function loadSdk(): Promise<void> {
  if (window.MercadoPago) return Promise.resolve();
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = SDK_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loading = null;
      reject(new Error('No se pudo cargar Mercado Pago. Revisá tu conexión y recargá la página.'));
    };
    document.head.appendChild(script);
  });
  return loading;
}

export interface CardForm {
  identificationTypes: { id: string; name: string }[];
  /** Token de la tarjeta, o Error con lo que falta. */
  createToken: (holder: string, docType: string, docNumber: string) => Promise<string>;
  unmount: () => void;
}

const LABELS: Record<FieldName, string> = {
  cardNumber: 'el número de tarjeta',
  expirationDate: 'el vencimiento',
  securityCode: 'el código de seguridad',
};
const PLACEHOLDERS: Record<FieldName, string> = {
  cardNumber: '1234 1234 1234 1234',
  expirationDate: 'MM/AA',
  securityCode: '123',
};

export async function mountCardForm(opts: {
  publicKey: string;
  containers: Record<FieldName, string>;
  onFocus: (field: FieldName, focused: boolean) => void;
}): Promise<CardForm> {
  await loadSdk();
  const mp = new window.MercadoPago!(opts.publicKey, { locale: 'es-AR' });
  const body = getComputedStyle(document.body);
  const style = {
    fontSize: '14px',
    fontFamily: body.fontFamily,
    color: body.color,
    placeholderColor: getComputedStyle(document.documentElement)
      .getPropertyValue('--mantine-color-placeholder')
      .trim(),
  };
  const valid: Record<FieldName, boolean> = { cardNumber: false, expirationDate: false, securityCode: false };
  const fields = {} as Record<FieldName, Field>;
  for (const name of Object.keys(PLACEHOLDERS) as FieldName[]) {
    const field = mp.fields
      .create(name, { placeholder: PLACEHOLDERS[name], style })
      .mount(opts.containers[name]);
    field.on('validityChange', ((e: { errorMessages?: unknown[] }) => {
      valid[name] = !e.errorMessages?.length;
    }) as never);
    field.on('focus', (() => opts.onFocus(name, true)) as never);
    field.on('blur', (() => opts.onFocus(name, false)) as never);
    fields[name] = field;
  }
  fields.cardNumber.on('binChange', (async (e: { bin?: string }) => {
    if (!e.bin) return;
    try {
      const { results } = await mp.getPaymentMethods({ bin: e.bin });
      const length = results[0]?.settings?.[0]?.security_code?.length;
      if (length) fields.securityCode.update({ settings: { mode: 'mandatory', length } });
    } catch {
      // sin datos de la tarjeta: queda el largo por defecto
    }
  }) as never);

  let identificationTypes: { id: string; name: string }[];
  try {
    identificationTypes = await mp.getIdentificationTypes();
  } catch {
    identificationTypes = [{ id: 'DNI', name: 'DNI' }];
  }

  return {
    identificationTypes,
    createToken: async (holder, docType, docNumber) => {
      // MP avisa la validez al salir de cada campo: si se toca "Pagar" justo despues, llega un instante tarde.
      const missing = () => (Object.keys(valid) as FieldName[]).find((name) => !valid[name]);
      if (missing()) await new Promise((r) => setTimeout(r, 500));
      const field = missing();
      if (field) throw new Error(`Revisá ${LABELS[field]}.`);
      try {
        const token = await mp.fields.createCardToken({
          cardholderName: holder,
          identificationType: docType,
          identificationNumber: docNumber,
        });
        return token.id;
      } catch {
        throw new Error('No pudimos validar la tarjeta. Revisá los datos y probá de nuevo.');
      }
    },
    unmount: () => Object.values(fields).forEach((f) => f.unmount()),
  };
}

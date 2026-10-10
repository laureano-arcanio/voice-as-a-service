// SDK de Mercado Pago (v2) para el Card Payment Brick: los campos de la tarjeta son iframes de MP y la
// tarjeta vuelve tokenizada (`token`), que va a la API como card_token_id. Se carga solo en /plan/pagar,
// la unica pagina cuya CSP lo permite (app/api/http.py, MP_PAGES).

const SDK_URL = 'https://sdk.mercadopago.com/js/v2';

export interface CardFormData {
  token: string;
  payment_method_id: string;
  payer?: { email?: string; identification?: { type: string; number: string } };
}

export interface BrickController {
  unmount: () => void;
}

interface MercadoPagoInstance {
  bricks: () => {
    create: (brick: 'cardPayment', containerId: string, settings: unknown) => Promise<BrickController>;
  };
}

declare global {
  interface Window {
    MercadoPago?: new (publicKey: string, options?: { locale?: string }) => MercadoPagoInstance;
  }
}

let loading: Promise<void> | null = null;

export function loadSdk(): Promise<void> {
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

export async function mountCardBrick(opts: {
  publicKey: string;
  containerId: string;
  amount: number;
  email: string;
  onSubmit: (data: CardFormData) => Promise<void>;
  onReady: () => void;
  onError: (message: string) => void;
}): Promise<BrickController> {
  await loadSdk();
  const mp = new window.MercadoPago!(opts.publicKey, { locale: 'es-AR' });
  return mp.bricks().create('cardPayment', opts.containerId, {
    initialization: { amount: opts.amount, payer: { email: opts.email } },
    customization: {
      paymentMethods: { maxInstallments: 1, minInstallments: 1 },
      visual: { style: { theme: 'default' }, hidePaymentButton: false },
    },
    callbacks: {
      onReady: opts.onReady,
      onSubmit: (data: CardFormData) => opts.onSubmit(data),
      onError: (error: { message?: string }) =>
        opts.onError(error?.message ?? 'Error del formulario de pago'),
    },
  });
}

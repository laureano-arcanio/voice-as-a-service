// Card Payment Brick de Mercado Pago (SDK v2) para el paso del pago del registro. Los campos de la tarjeta
// son iframes de MP; la tarjeta vuelve tokenizada (`token`) y va a la API como card_token_id.
import { UserFacingError } from "./errors";

const SDK_URL = "https://sdk.mercadopago.com/js/v2";

export interface CardFormData {
  token: string;
  payment_method_id: string;
}

export interface BrickController {
  unmount: () => void;
}

interface MercadoPagoInstance {
  bricks: () => { create: (brick: "cardPayment", containerId: string, settings: unknown) => Promise<BrickController> };
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
    const script = document.createElement("script");
    script.src = SDK_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loading = null;
      reject(new UserFacingError("No se pudo cargar Mercado Pago. Revisá tu conexión y recargá la página."));
    };
    document.head.appendChild(script);
  });
  return loading;
}

/** Los colores y radios del brick salen de los tokens de la landing (global.css), no de hex sueltos. */
function themeVariables(): Record<string, string> {
  const css = getComputedStyle(document.documentElement);
  const token = (name: string) => css.getPropertyValue(`--color-${name}`).trim();
  return {
    baseColor: token("accent"),
    baseColorFirstVariant: token("accent-2"),
    baseColorSecondVariant: token("accent-2"),
    // Borde de los campos en gris, como los de la landing; el foco toma baseColor (acento).
    outlinePrimaryColor: token("line-2"),
    outlineSecondaryColor: token("line"),
    textPrimaryColor: token("ink"),
    textSecondaryColor: token("muted"),
    inputBackgroundColor: token("bg-2"),
    formBackgroundColor: token("surface"),
    errorColor: token("warn"),
    successColor: token("ok"),
    buttonTextColor: token("accent-ink"),
    borderRadiusSmall: "10px",
    borderRadiusMedium: "12px",
    borderRadiusLarge: "10px",
    formPadding: "0px",
  };
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
  const mp = new window.MercadoPago!(opts.publicKey, { locale: "es-AR" });
  return mp.bricks().create("cardPayment", opts.containerId, {
    initialization: { amount: opts.amount, payer: { email: opts.email } },
    customization: {
      paymentMethods: { maxInstallments: 1, minInstallments: 1 },
      visual: {
        hideFormTitle: true,
        style: { theme: "default", customVariables: themeVariables() },
        texts: { formSubmit: "Pagar y crear mi cuenta" },
      },
    },
    callbacks: {
      onReady: opts.onReady,
      onSubmit: (data: CardFormData) => opts.onSubmit(data),
      onError: (error: { message?: string }) => opts.onError(error?.message ?? "Error del formulario de pago"),
    },
  });
}

import { ApiError, checkSignupEmail, publicPlans, signup, type PublicPlans } from "./api";
import { track } from "./analytics";
import { UserFacingError } from "./errors";
import { type BrickController, mountCardBrick } from "./mercadopago";

const TAKEN = "Ya hay una cuenta con ese email. Ingresá en app.atentina.com.ar o recuperá tu clave.";
const CONTAINER = "signup-card-brick";

const money = (n: number) => `$ ${n.toLocaleString("es-AR")}`;
const REDIRECT_SECONDS = 5;

/** Formulario de /registro. El plan elegido en los precios llega como ?plan=<nombre>. Con un plan pago y
 * Mercado Pago, el paso 2 es el pago con tarjeta; la cuenta se crea con el pago aprobado. */
export function initSignupForm(root: HTMLElement) {
  const form = root.querySelector<HTMLFormElement>("[data-signup-form]")!;
  const submit = root.querySelector<HTMLButtonElement>("[data-signup-submit]")!;
  const submitLabel = root.querySelector<HTMLElement>("[data-submit-label]")!;
  const error = root.querySelector<HTMLElement>("[data-signup-error]")!;
  const sent = root.querySelector<HTMLElement>("[data-signup-sent]")!;
  const payError = root.querySelector<HTMLElement>("[data-pay-error]")!;
  const payLoading = root.querySelector<HTMLElement>("[data-pay-loading]")!;
  const password = form.elements.namedItem("password") as HTMLInputElement;
  const confirm = form.elements.namedItem("confirm") as HTMLInputElement;
  const match = () => confirm.setCustomValidity(confirm.value === password.value ? "" : "Las claves no coinciden.");
  password.addEventListener("input", match);
  confirm.addEventListener("input", match);

  const plan = new URLSearchParams(location.search).get("plan")?.replace(/[^\w .-]/g, "").slice(0, 64) ?? "";
  let catalog: PublicPlans | null = null;
  let brick: BrickController | null = null;
  const setState = (state: string) => (root.dataset.state = state);

  /** El plan elegido, si es pago y se contrata en el registro. */
  const paidPlan = () => catalog?.plans.find((p) => p.name.toLowerCase() === plan.toLowerCase()) ?? null;
  const paysHere = () => !!(paidPlan() && catalog?.mp_public_key);

  // Texto e items de la izquierda segun el plan (los renderiza la pagina; aca se elige cual se ve).
  const showIntro = (key: string) => {
    document.querySelectorAll<HTMLElement>("[data-intro], [data-intro-list]").forEach((el) => {
      el.hidden = (el.dataset.intro ?? el.dataset.introList) !== key;
    });
  };

  const values = () => {
    const data = new FormData(form);
    const value = (name: string) => String(data.get(name) ?? "").trim();
    return {
      company: value("company"),
      name: value("name"),
      email: value("email"),
      password: password.value,
      plan,
      website: value("website"),
    };
  };

  /** Pantalla final: check, mensaje, boton al panel y cuenta regresiva (el link de la sesion vale 10 min). */
  const finish = (url: string, paidName?: string) => {
    root.querySelector("[data-sent-title]")!.textContent = paidName ? "Pago aprobado" : "Cuenta creada";
    root.querySelector("[data-sent-text]")!.textContent = paidName
      ? `Tu plan ${paidName} ya está activo. Te mandamos el comprobante por mail.`
      : "Tu cuenta ya está lista. Armá tu agente y probalo con una llamada de prueba.";
    root.querySelector<HTMLAnchorElement>("[data-sent-go]")!.href = url;
    // Solo el recuadro, centrado: sin el texto ni la lista del plan a la izquierda.
    document.querySelectorAll<HTMLElement>("[data-intro], [data-intro-list]").forEach((el) => (el.hidden = true));
    const page = document.querySelector<HTMLElement>("[data-signup-page]");
    if (page) page.dataset.done = "";
    setState("sent");
    track("sign_up", { method: "landing", plan: plan || "free" });
    sent.focus();
    const count = root.querySelector<HTMLElement>("[data-sent-count]")!;
    let left = REDIRECT_SECONDS;
    count.textContent = String(left);
    const timer = setInterval(() => {
      left -= 1;
      count.textContent = String(Math.max(left, 0));
      if (left <= 0) {
        clearInterval(timer);
        location.assign(url);
      }
    }, 1000);
  };

  const failMessage = (e: unknown) =>
    e instanceof ApiError && e.code === "email_taken"
      ? TAKEN
      : e instanceof UserFacingError
        ? e.message
        : "No pudimos crear la cuenta. Probá de nuevo o escribinos por WhatsApp.";

  // Paso 2: el brick se monta una vez (con el email del paso 1) y se reusa si vuelve a corregir datos.
  const showPayment = async () => {
    const chosen = paidPlan()!;
    root.querySelector("[data-pay-plan]")!.textContent = chosen.name;
    root.querySelector("[data-pay-price]")!.textContent = money(chosen.price_ars);
    setState("pay");
    payError.textContent = "";
    if (brick) return;
    payLoading.hidden = false;
    try {
      brick = await mountCardBrick({
        publicKey: catalog!.mp_public_key!,
        containerId: CONTAINER,
        amount: chosen.price_ars,
        email: values().email,
        onReady: () => (payLoading.hidden = true),
        onError: (message) => (payError.textContent = message),
        onSubmit: async (card) => {
          setState("paying");
          payError.textContent = "";
          try {
            finish(await signup({ ...values(), card_token_id: card.token }), paidPlan()!.name);
          } catch (e) {
            if (e instanceof ApiError && e.code === "email_taken") {
              setState("idle");
              error.textContent = TAKEN;
            } else {
              setState("pay");
              payError.textContent = failMessage(e);
            }
            throw e; // el brick vuelve a habilitar el botón
          }
        },
      });
    } catch (e) {
      payLoading.hidden = true;
      payError.textContent = failMessage(e);
    }
  };

  root.querySelector("[data-pay-back]")!.addEventListener("click", () => {
    setState("idle");
    error.textContent = "";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    match();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    error.textContent = "";
    try {
      if (paysHere()) {
        setState("checking");
        await checkSignupEmail(values().email);
        await showPayment();
      } else {
        setState("sending");
        finish(await signup(values()));
      }
    } catch (e) {
      setState("idle");
      error.textContent = failMessage(e);
    } finally {
      submit.disabled = false;
    }
  });

  // Plan pago: el paso 1 y el texto de la izquierda cambian segun lo que diga la API (precio y si hay MP).
  if (plan) {
    publicPlans()
      .then((plans) => {
        catalog = plans;
        const chosen = paidPlan();
        if (!chosen) return;
        showIntro(chosen.name.toLowerCase());
        document.title = `Contratá el plan ${chosen.name} · Atentina`;
        if (paysHere()) {
          root.querySelector<HTMLElement>("[data-step-one]")!.hidden = false;
          submitLabel.textContent = "Continuar al pago";
        } else {
          const note = root.querySelector<HTMLElement>("[data-signup-plan]")!;
          note.querySelector("b")!.textContent = chosen.name;
          note.hidden = false;
        }
      })
      .catch(() => {
        // Sin la API de planes, el registro sigue: la cuenta se crea y el plan se paga desde el panel.
      });
  }
}

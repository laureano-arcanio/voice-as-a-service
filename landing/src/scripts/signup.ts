import { signup } from "./api";
import { track } from "./analytics";
import { UserFacingError } from "./errors";

/** Formulario de /registro. El plan elegido en los precios llega como ?plan=<nombre>. */
export function initSignupForm(root: HTMLElement) {
  const form = root.querySelector<HTMLFormElement>("[data-signup-form]")!;
  const submit = root.querySelector<HTMLButtonElement>("[data-signup-submit]")!;
  const error = root.querySelector<HTMLElement>("[data-signup-error]")!;
  const sent = root.querySelector<HTMLElement>("[data-signup-sent]")!;
  const sentEmail = root.querySelector<HTMLElement>("[data-signup-email]")!;
  const plan = new URLSearchParams(location.search).get("plan")?.replace(/[^\w .-]/g, "").slice(0, 64) ?? "";
  const planNote = root.querySelector<HTMLElement>("[data-signup-plan]");
  if (plan && planNote) {
    planNote.querySelector("b")!.textContent = plan;
    planNote.hidden = false;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const value = (name: string) => String(data.get(name) ?? "").trim();
    root.dataset.state = "sending";
    submit.disabled = true;
    error.textContent = "";
    try {
      await signup({ company: value("company"), name: value("name"), email: value("email"), plan, website: value("website") });
      sentEmail.textContent = value("email");
      root.dataset.state = "sent";
      track("sign_up", { method: "landing", plan: plan || "free" });
      sent.focus();
    } catch (e) {
      root.dataset.state = "idle";
      error.textContent =
        e instanceof UserFacingError ? e.message : "No pudimos crear la cuenta. Probá de nuevo o escribinos por WhatsApp.";
    } finally {
      submit.disabled = false;
    }
  });
}

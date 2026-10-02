import { sendContact } from "./api";
import { track } from "./analytics";
import { UserFacingError } from "./errors";

const NEED_CONTACT = "Dejanos un email o un teléfono para contactarte.";

export function initContactForm(root: HTMLElement) {
  const form = root.querySelector<HTMLFormElement>("[data-contact-form]")!;
  const submit = root.querySelector<HTMLButtonElement>("[data-contact-submit]")!;
  const error = root.querySelector<HTMLElement>("[data-contact-error]")!;
  const sent = root.querySelector<HTMLElement>("[data-contact-sent]")!;
  const email = form.elements.namedItem("email") as HTMLInputElement;
  const phone = form.elements.namedItem("phone") as HTMLInputElement;

  const requireOne = () => email.setCustomValidity(email.value.trim() || phone.value.trim() ? "" : NEED_CONTACT);
  email.addEventListener("input", requireOne);
  phone.addEventListener("input", requireOne);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    requireOne();
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const value = (name: string) => String(data.get(name) ?? "").trim();
    root.dataset.state = "sending";
    submit.disabled = true;
    error.textContent = "";
    try {
      await sendContact({
        name: value("name"),
        company: value("company"),
        email: value("email") || null,
        phone: value("phone"),
        message: value("message"),
        page: location.pathname.toLowerCase().replace(/[^a-z0-9/_-]/g, "").slice(0, 64),
        website: value("website"),
      });
      root.dataset.state = "sent";
      track("generate_lead", { method: "formulario", page: location.pathname });
      sent.focus();
    } catch (e) {
      root.dataset.state = "idle";
      error.textContent =
        e instanceof UserFacingError ? e.message : "No pudimos enviar tu pedido. Probá de nuevo o escribinos por WhatsApp.";
    } finally {
      submit.disabled = false;
    }
  });
}

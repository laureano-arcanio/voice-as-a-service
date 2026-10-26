import { sendConsumerRequest } from "./api";
import { UserFacingError } from "./errors";

/** Formulario de los botones de arrepentimiento y de baja: manda el pedido y muestra el código de trámite. */
export function initConsumerRequestForm(root: HTMLElement) {
  const form = root.querySelector<HTMLFormElement>("[data-request-form]")!;
  const submit = root.querySelector<HTMLButtonElement>("[data-request-submit]")!;
  const error = root.querySelector<HTMLElement>("[data-request-error]")!;
  const sent = root.querySelector<HTMLElement>("[data-request-sent]")!;
  const kind = root.dataset.kind as "revocation" | "cancellation";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const value = (name: string) => String(data.get(name) ?? "").trim();
    root.dataset.state = "sending";
    submit.disabled = true;
    error.textContent = "";
    try {
      const code = await sendConsumerRequest({
        kind,
        name: value("name"),
        email: value("email"),
        company: value("company"),
        message: value("message"),
        website: value("website"),
      });
      root.querySelector("[data-request-code]")!.textContent = code;
      root.dataset.state = "sent";
      sent.focus();
    } catch (e) {
      root.dataset.state = "idle";
      error.textContent =
        e instanceof UserFacingError ? e.message : "No pudimos enviar tu pedido. Probá de nuevo o escribinos a hola@atentina.com.ar.";
    } finally {
      submit.disabled = false;
    }
  });
}

// Email Worker de Cloudflare para las casillas de prospección (docs/CRM_PLAN.md, 6).
// Reenvía cada mail a Gmail, como la regla anterior, y una copia al CRM (Resend Receiving).
// Las dos direcciones tienen que estar verificadas en Email Routing → Destination addresses.
// Se asigna en Email Routing → Routing rules: laureano@atentina.net (y .com.ar) → "Send to a Worker".
const GMAIL = "larcanio@gmail.com";
const CRM = "crm@in.atentina.net";

export default {
  async email(message) {
    await message.forward(GMAIL);
    try {
      await message.forward(CRM);
    } catch (e) {
      // Si el CRM falla, el mail igual llegó a Gmail
      console.log(`CRM: ${e}`);
    }
  },
};

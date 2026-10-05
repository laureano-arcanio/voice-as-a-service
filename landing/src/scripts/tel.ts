const QR_URL = "https://cdnjs.cloudflare.com/ajax/libs/qrcode-generator/1.4.4/qrcode.min.js";

interface QrCode {
  addData(data: string): void;
  make(): void;
  createSvgTag(options: { cellSize: number; margin: number; scalable: boolean }): string;
}

declare global {
  interface Window {
    qrcode?: (type: number, level: string) => QrCode;
  }
}

let qrLoading: Promise<void> | null = null;

function loadQr(): Promise<void> {
  qrLoading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = QR_URL;
    script.onload = () => resolve();
    script.onerror = () => {
      qrLoading = null;
      reject(new Error("qr"));
    };
    document.head.appendChild(script);
  });
  return qrLoading;
}

export function initTelDialog() {
  const dialog = document.querySelector<HTMLDialogElement>("#tel");
  if (!dialog) return;
  const number = dialog.querySelector<HTMLAnchorElement>("[data-tel-number]")!;
  const agent = dialog.querySelector<HTMLElement>("[data-tel-agent]")!;
  const qrBox = dialog.querySelector<HTMLElement>("[data-tel-qr]")!;
  const qr = dialog.querySelector<HTMLElement>("[data-qr]")!;
  let drawn = "";

  function setNumber(tel: string, display: string) {
    number.textContent = display;
    number.href = `tel:${tel}`;
  }

  async function drawQr(tel: string) {
    try {
      await loadQr();
    } catch {
      return;
    }
    if (!window.qrcode || drawn === tel) {
      qrBox.hidden = drawn !== tel;
      return;
    }
    const code = window.qrcode(0, "M");
    code.addData(`tel:${tel}`);
    code.make();
    qr.innerHTML = code.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
    qr.firstElementChild?.classList.add("block", "size-full");
    drawn = tel;
    qrBox.hidden = false;
  }

  document.addEventListener("click", (event) => {
    const link = (event.target as Element).closest("[data-open-tel]");
    if (!link) return;
    event.preventDefault();
    const widget = link.closest("[data-call]");
    const checked = widget?.querySelector<HTMLInputElement>("input[name=agente]:checked");
    if (!checked?.dataset.tel) return;
    agent.textContent = checked.dataset.title ?? "";
    const tel = checked.dataset.tel;
    setNumber(tel, checked.dataset.telDisplay ?? tel);
    const phone = window.matchMedia("(pointer: coarse)").matches && window.innerWidth < 900;
    if (phone) qrBox.hidden = true;
    else void drawQr(tel);
    dialog.showModal();
  });
}

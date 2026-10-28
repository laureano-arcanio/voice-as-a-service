import puppeteer from 'puppeteer-core';
export const base = 'http://127.0.0.1:5177';
export const out = '/home/laureano/voice-as-a-service/marketing/videos/public/proyectos/llamadas-salientes/capturas';
export const wait = (ms = 800) => new Promise((r) => setTimeout(r, ms));
export async function abrir(w = 1600, h = 900, dpr = 1.2) {
  const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new',
    args: ['--no-sandbox', '--disable-spell-checking', '--lang=es-ES', '--use-fake-ui-for-media-stream'] });
  const page = await browser.newPage();
  await page.emulateTimezone('America/Argentina/Buenos_Aires');
  // Chrome informa el alias viejo (America/Buenos_Aires), que el Python del venv local no conoce
  await page.evaluateOnNewDocument(() => {
    const o = Intl.DateTimeFormat.prototype.resolvedOptions;
    Intl.DateTimeFormat.prototype.resolvedOptions = function () { const r = o.call(this); if (r.timeZone === 'America/Buenos_Aires') r.timeZone = 'America/Argentina/Buenos_Aires'; return r; };
  });
  await page.setViewport({ width: w, height: h, deviceScaleFactor: dpr });
  page.on('pageerror', (e) => console.log('page error:', String(e).slice(0, 300)));
  return { browser, page };
}
export const login = async (page, email, pass, path = '/login') => {
  await page.goto(`${base}${path}`, { waitUntil: 'networkidle0' });
  await page.type('input[type=email]', email); await page.type('input[type=password]', pass);
  await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {}), page.click('button[type=submit]')]);
  await wait(1200);
};
export const clickText = (page, txt, sel = 'button, [role=tab], a, label, [role=option]') => page.evaluate((txt, sel) => {
  const els = [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length);
  const el = els.find((b) => b.textContent.trim() === txt) ?? els.find((b) => b.textContent.trim().includes(txt));
  el?.click(); return !!el;
}, txt, sel);
export const sinSpell = (page) => page.evaluate(() => document.querySelectorAll('input,textarea').forEach((e) => e.setAttribute('spellcheck', 'false')));
export const inicio = async (page) => { await login(page, 'dev@miempresa.example', 'clave-demo-123'); await clickText(page, 'Explorar el panel', 'button'); await wait(500); };

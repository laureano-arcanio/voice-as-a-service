// Utilidades para las capturas del video tutorial-agente-free-mobile (390 x 844, DPR 2).
import puppeteer from 'puppeteer-core';
export const base = 'http://127.0.0.1:5175';
export async function open() {
  const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new',
    env: { ...process.env, LANG: 'es_ES.UTF-8', LANGUAGE: 'es_ES:es', LC_ALL: 'es_ES.UTF-8' },
    args: ['--no-sandbox', '--disable-spell-checking', '--lang=es-ES', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] });
  await (await browser.pages())[0]?.close();
  const page = await browser.newPage();
  await page.emulateTimezone('America/Argentina/Buenos_Aires');
  await page.setExtraHTTPHeaders({ 'Accept-Language': 'es-ES,es;q=0.9' });
  await page.evaluateOnNewDocument(() => {
    document.addEventListener('DOMContentLoaded', () => { document.documentElement.setAttribute('spellcheck', 'false'); document.body.setAttribute('spellcheck', 'false'); });
  });
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  page.on('pageerror', (e) => console.log('page error:', String(e).slice(0, 300)));
  return { browser, page };
}
export const wait = (ms = 800) => new Promise((r) => setTimeout(r, ms));
export const clickText = (page, txt, sel = 'button, [role=tab], a, label, [role=menuitem], [role=option]') =>
  page.evaluate((txt, sel) => {
    const els = [...document.querySelectorAll(sel)].filter((e) => e.offsetParent !== null || e.getClientRects().length);
    const el = els.find((b) => b.textContent.trim() === txt) ?? els.find((b) => b.textContent.trim().includes(txt));
    el?.click();
    return !!el;
  }, txt, sel);
/** Centro (CSS px) del elemento visible con ese texto, para dibujar el toque. */
export const where = (page, txt, sel = 'button, [role=tab], a, label, [role=menuitem], [role=option], input, textarea') =>
  page.evaluate((txt, sel) => {
    const els = [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length);
    const el = els.find((b) => b.textContent.trim() === txt || b.getAttribute('aria-label') === txt) ?? els.find((b) => b.textContent.trim().includes(txt));
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
  }, txt, sel);
export async function login(page, email = 'marta@elfogon.example', pass = 'clave-demo-123') {
  await page.goto(`${base}/login`, { waitUntil: 'networkidle0' });
  await page.type('input[type=email]', email);
  await page.type('input[type=password]', pass);
  await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {}), page.click('button[type=submit]')]);
  await wait();
}

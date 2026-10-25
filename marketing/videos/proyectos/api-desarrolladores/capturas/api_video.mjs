// Capturas del panel para el video api-desarrolladores (1600 x 900, DPR 1,2 = 1920 x 1080).
// Backend aislado :8114 (capturas/backend.sh) + Vite :5176. La key creada (del backend aislado) se tapa en el DOM.
import puppeteer from 'puppeteer-core';
const base = 'http://127.0.0.1:5176';
const out = '/home/laureano/voice-as-a-service/marketing/videos/public/proyectos/api-desarrolladores/capturas';
const wait = (ms = 800) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new',
  args: ['--no-sandbox', '--disable-spell-checking', '--lang=es-ES'] });
const page = await browser.newPage();
await page.emulateTimezone('America/Argentina/Buenos_Aires');
await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1.2 });
page.on('pageerror', (e) => console.log('page error:', String(e).slice(0, 300)));
// Tapa la key (la del backend aislado) y pone el dominio publico en vez del de desarrollo
const limpiar = () => page.evaluate(() => {
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; while ((n = w.nextNode())) n.nodeValue = n.nodeValue.replace(/vaas_[A-Za-z0-9_\-]+/g, 'vaas_••••••••••••••••')
    .replaceAll('http://127.0.0.1:5176', 'https://app.atentina.com.ar');
});
const clickText = (txt, sel = 'button, [role=tab], a, label') => page.evaluate((txt, sel) => {
  const els = [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length);
  const el = els.find((b) => b.textContent.trim() === txt) ?? els.find((b) => b.textContent.trim().includes(txt));
  el?.click(); return !!el;
}, txt, sel);
await page.goto(`${base}/login`, { waitUntil: 'networkidle0' });
await page.type('input[type=email]', 'dev@miempresa.example');
await page.type('input[type=password]', 'clave-demo-123');
await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {}), page.click('button[type=submit]')]);
await wait(1500);
await page.goto(`${base}/developers`, { waitUntil: 'networkidle0' });
await wait(1200);
await limpiar();
await page.screenshot({ path: `${out}/01-api.png` });
console.log('nueva', await clickText('Nueva API key', 'button'));
await wait(900);
await page.type('[role=dialog] input[type=text], [role=dialog] input:not([type])', 'Mi app');
for (const l of ['LLM', 'Síntesis (TTS)']) console.log(l, await clickText(l, '[role=dialog] label'));
await wait(600);
await limpiar();
await page.screenshot({ path: `${out}/02-nueva-key.png` });
console.log('crear', await clickText('Crear', '[role=dialog] button'));
await wait(1500);
await limpiar();
await page.screenshot({ path: `${out}/03-key-creada.png` });
await browser.close();

// Capturas para el video derivaciones (390 x 844, DPR 2), como cliente de ejemplo "Aires del Sur" (ficticio),
// contra el backend aislado :8112 + Vite :5174. La llamada derivada del final es un mock (GET interceptado).
// uso (desde scratch/shots): node derivaciones_video.mjs
import puppeteer from 'puppeteer-core';
const out = '../videos/derivaciones/shots';
const base = 'http://127.0.0.1:5174';
const FAKE = '0e0e0e0e-0000-4000-8000-000000000042';
const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new', env: { ...process.env, LANG: 'es_ES.UTF-8', LANGUAGE: 'es_ES:es', LC_ALL: 'es_ES.UTF-8' }, args: ['--no-sandbox', '--disable-spell-checking', '--lang=es-ES'] });
await (await browser.pages())[0]?.close();
const page = await browser.newPage();
await page.emulateTimezone('America/Montevideo');
await page.setExtraHTTPHeaders({ 'Accept-Language': 'es-ES,es;q=0.9' });
await page.evaluateOnNewDocument(() => {
  document.addEventListener('DOMContentLoaded', () => { document.documentElement.setAttribute('spellcheck', 'false'); document.body.setAttribute('spellcheck', 'false'); });
});
await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });
const at = (s) => new Date(Date.UTC(2026, 9, 23, 14, 12, s)).toISOString();
const msgs = [
  { role: 'assistant', text: 'Hola, gracias por llamar a Aires del Sur. Te habla Sofía, la asistente virtual. ¿En qué te puedo ayudar?' },
  { role: 'user', text: 'Hola, quiero un presupuesto para instalar dos splits en casa.' },
  { role: 'assistant', text: 'Para presupuestos te paso con Ventas. Un momento, por favor.' },
  { role: 'assistant', text: 'Hola, soy Lucía de Ventas. Me cuentan que querés instalar dos splits.', handoff_leg: 'leg-1', person: 'Lucía Romero' },
  { role: 'user', text: 'Sí, uno en el living y otro en el dormitorio.', handoff_leg: 'leg-1' },
  { role: 'assistant', text: 'Perfecto. Te coordino una visita técnica para el jueves a la mañana.', handoff_leg: 'leg-1', person: 'Lucía Romero' },
].map((m, i) => ({ llm: null, voice_note: false, recording: null, handoff_leg: null, person: null, at: at(i * 11), ...m }));
let clientId = null, agentId = null, agentName = null;
await page.setRequestInterception(true);
page.on('request', (req) => {
  const u = new URL(req.url());
  if (req.method() === 'GET' && u.pathname === `/api/v1/calls/${FAKE}`) {
    return req.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({
      id: FAKE, client_id: clientId, client_name: 'Aires del Sur', agent_id: agentId, agent_name: agentName, agent_version: 2,
      created_at: at(0), workflow_status: 'completed',
      fields: [
        { name: 'consulta', description: 'Qué necesita o pregunta la persona, en una frase.', value: 'Presupuesto para instalar dos splits', required: true },
        { name: 'nombre', description: 'Nombre y apellido de la persona.', value: 'Marcos Vera', required: false },
      ],
      outcome: { label: 'Derivada al equipo', goal: true }, messages: msgs, context: null, recordings: [],
      call: { mode: 'inbound', phone: '+5493515550100', client_number: '+5493516667788', status: 'finalizada', ended_reason: 'completed',
        error: '', duration_seconds: 142, latency: null, created_at: at(0), started_at: at(1), ended_at: at(143) },
    }) });
  }
  if (req.method() === 'POST' && u.pathname.startsWith('/api/v1/calls')) return req.abort();
  return req.continue();
});
page.on('pageerror', (e) => console.log('page error:', String(e).slice(0, 300)));
const wait = (ms = 800) => new Promise((r) => setTimeout(r, ms));
const click = (txt, sel = 'button, [role=tab], a, label, [role=menuitem], [role=option]') =>
  page.evaluate((txt, sel) => {
    const els = [...document.querySelectorAll(sel)].filter((e) => e.offsetParent !== null || e.getClientRects().length);
    const el = els.find((b) => b.textContent.trim() === txt) ?? els.find((b) => b.textContent.trim().includes(txt));
    el?.click();
    return !!el;
  }, txt, sel);
const toDivider = async (txt) => {
  await page.evaluate((txt) => {
    const d = [...document.querySelectorAll('.mantine-Divider-label')].find((x) => x.textContent.includes(txt));
    d?.scrollIntoView({ block: 'start' });
    let el = d?.parentElement;
    while (el && !(el.scrollHeight > el.clientHeight + 2 && getComputedStyle(el).overflowY !== 'visible')) el = el.parentElement;
    if (el) el.scrollTop -= 90;
  }, txt);
  await wait(400);
};
const shot = async (name, full = false) => { await page.screenshot({ path: `${out}/${name}.png`, fullPage: full }); console.log('ok', name); };

await page.goto(`${base}/login`, { waitUntil: 'networkidle0' });
await page.type('input[type=email]', 'carla@airesdelsur.example');
await page.type('input[type=password]', 'clave-demo-123');
await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {}), page.click('button[type=submit]')]);
await wait();
const me = await page.evaluate(async () => (await fetch('/api/v1/auth/me')).json());
clientId = me.client_id;
const agents = await page.evaluate(async () => (await fetch('/api/v1/agents')).json());
agentId = agents[0].id; agentName = agents[0].name;

// Menú con Equipo
await page.goto(`${base}/team`, { waitUntil: 'networkidle0' });
await wait();
await page.click('button[aria-label]').catch(() => {});
await wait();
await shot('01-menu');
await page.goto(`${base}/team`, { waitUntil: 'networkidle0' });
await wait();
await shot('02-equipo');
await shot('02-equipo-full', true);

// Persona nueva
console.log('agregar', await click('Agregar persona'));
await wait();
await page.type('.mantine-Modal-body input[maxlength="120"]', 'Lucía Romero');
await page.type('.mantine-Modal-body input[placeholder="351 555-1234"]', '351 555-0142');
await wait(300);
await shot('03-persona');
await page.click('.mantine-Modal-body button[type=submit]');
await wait(1500);
await shot('04-equipo-con-lucia');

// Área nueva
console.log('area', await click('Crear área'));
await wait();
await page.type('.mantine-Modal-body input[maxlength="80"]', 'Ventas');
await page.type('.mantine-Modal-body textarea', 'Precios, presupuestos de instalación y visitas al showroom.');
for (const n of ['Lucía Romero', 'Diego Ferreyra']) {
  await page.click('.mantine-Modal-body input[placeholder="Agregar persona"]');
  await wait(400);
  console.log('opt', n, await click(n, '[role=option]'));
  await wait(400);
}
await shot('05-area-top');
// Horario: deja de atender siempre y suma el sábado
await page.evaluate(() => {
  const l = [...document.querySelectorAll('.mantine-Modal-body label')].find((x) => x.textContent.trim().startsWith('Atiende siempre'));
  l?.click();
});
await wait(500);
await page.click('[aria-label="Agregar franja el sábado"]');
await wait(300);
await page.evaluate(() => {
  const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
  const h = document.querySelector('[aria-label="Sábado, franja 1, hasta"]'); if (h) set(h, '13:00');
});
await wait(300);
await toDivider('Personas');
await shot('06-area-personas');
await toDivider('Horario');
await shot('07-area-horario');
await toDivider('Durante la llamada');
await shot('08-area-llamada');
await toDivider('Mensajes');
await shot('09-area-mensajes');
await page.click('.mantine-Modal-body button[type=submit]');
await wait(1500);
await page.evaluate(() => {
  const t = [...document.querySelectorAll('h4')].find((x) => x.textContent.trim() === 'Áreas');
  t?.scrollIntoView({ block: 'start' });
  window.scrollBy(0, -70);
});
await wait(500);
await shot('10-areas');

// Agente: Derivación a personas
await page.goto(`${base}/agents/${agentId}`, { waitUntil: 'networkidle0' });
await wait(1000);
console.log('tab', await click('Definición', '[role=tab]'));
await wait(1200);
const scrollSec = async () => { await page.evaluate(() => document.getElementById('def-derivacion')?.scrollIntoView({ block: 'start' })); await wait(500); };
await scrollSec();
await shot('11-agente-derivacion-vacia');
for (const n of ['Ventas', 'Soporte técnico', 'Administración']) {
  await page.evaluate((n) => {
    const items = [...document.querySelectorAll('#def-derivacion .def-item')];
    const it = items.find((x) => x.querySelector('p')?.textContent.trim() === n);
    it?.querySelector('input[type=checkbox]')?.click();
  }, n);
  await wait(300);
}
const ta = await page.evaluateHandle(() => {
  const it = [...document.querySelectorAll('#def-derivacion .def-item')].find((x) => x.querySelector('p')?.textContent.trim() === 'Ventas');
  return it.querySelector('textarea');
});
await ta.type('Cuando pide un presupuesto o quiere comprar un equipo.');
await wait(300);
await scrollSec();
await shot('12-agente-derivacion');
await page.evaluate(() => {
  const it = [...document.querySelectorAll('#def-derivacion .def-item')].find((x) => x.querySelector('p')?.textContent.trim() === 'Ventas');
  it?.scrollIntoView({ block: 'start' }); window.scrollBy(0, -80);
});
await wait(400);
await shot('12b-agente-ventas');
await shot('12-agente-full', true);
await page.evaluate(() => {
  const sw = [...document.querySelectorAll('#def-derivacion label')].find((x) => x.textContent.includes('Música de espera'));
  sw?.scrollIntoView({ block: 'center' });
});
await wait(400);
await shot('13-agente-musica');
console.log('guardar', await click('Guardar versión nueva'));
await wait(1500);
await shot('14-guardado');

// Resultado: la llamada derivada (mock)
await page.goto(`${base}/calls/${FAKE}`, { waitUntil: 'domcontentloaded' });
await wait(3500);
await shot('15-llamada');
await page.evaluate(() => document.querySelector('.chat-leg')?.scrollIntoView({ block: 'center' }));
await wait(500);
await shot('16-llamada-tramo');
await shot('16-llamada-full', true);
await browser.close();

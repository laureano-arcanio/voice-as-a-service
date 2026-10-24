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

await page.goto(`${base}/calls/${FAKE}`, { waitUntil: 'domcontentloaded' });
await wait(3500);
await page.evaluate(() => { const c = document.querySelector('.chat')?.closest('.mantine-Card-root'); c?.scrollIntoView({ block: 'start' }); window.scrollBy(0, -72); });
await wait(500);
await shot('16-llamada-tramo');
await browser.close();

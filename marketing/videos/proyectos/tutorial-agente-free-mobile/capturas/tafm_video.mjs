// Capturas del video tutorial-agente-free-mobile (390 x 844, DPR 2), como el cliente Free de ejemplo
// "El Fogón" (ficticio), contra el backend aislado :8113 + Vite :5175. La llamada de prueba, las
// conversaciones y la llamada por el link son mocks (GET interceptados y DOM de la pagina publica).
// uso (desde scratch/shots, con tafm_lib.mjs al lado): node tafm_video.mjs
import fs from 'node:fs';
import { open, wait, login, base, clickText, where } from './tafm_lib.mjs';
const out = '../videos/tafm/shots';
const taps = {};
let { browser, page } = await open();
const shot = async (n) => { await page.screenshot({ path: `${out}/${n}.png` }); console.log('ok', n); };
const tap = async (key, txt, sel) => { taps[key] = await where(page, txt, sel); console.log('tap', key, taps[key]); };

const FAKE_TEST = '0e0e0e0e-0000-4000-8000-000000000101';
const FAKE_WEB = '0e0e0e0e-0000-4000-8000-000000000102';
const at = (m, s) => new Date(Date.UTC(2026, 9, 24, 15, m, s)).toISOString();
const OPENING = 'Hola, gracias por comunicarte. Te habla Sofía, la asistente virtual. ¿En qué te puedo ayudar?';
const msg = (role, text, i, m0) => ({ role, text, llm: null, voice_note: false, recording: null, handoff_leg: null, person: null, at: at(m0, i * 6) });
const testMsgs = [
  [ 'assistant', OPENING ],
  [ 'user', '¿Qué precio tiene la parrillada para dos?' ],
  [ 'assistant', 'La parrillada para dos sale treinta y ocho mil pesos. ¿Te ayudo con algo más?' ],
].map(([r, t], i) => msg(r, t, i, 10));
const webMsgs = [
  [ 'assistant', OPENING ],
  [ 'user', 'Hola, ¿abren los lunes?' ],
  [ 'assistant', 'Los lunes está cerrado. Abrimos de martes a domingo, al mediodía y a la noche. ¿Algo más?' ],
  [ 'user', '¿Y cuánto sale la docena de empanadas?' ],
  [ 'assistant', 'La docena de empanadas sale dieciocho mil pesos. ¿Te ayudo con algo más?' ],
  [ 'user', 'No, gracias, con eso me alcanza.' ],
  [ 'assistant', 'Gracias por comunicarte. Que tengas un buen día.' ],
].map(([r, t], i) => msg(r, t, i, 32));
let clientId = null, agentId = null, agentName = null;
const detail = (id, mode, msgs, fields, outcome, dur, m0) => ({
  id, client_id: clientId, client_name: 'El Fogón', agent_id: agentId, agent_name: agentName, agent_version: 2,
  created_at: at(m0, 0), workflow_status: 'completed', fields, outcome, messages: msgs, context: null, recordings: [],
  call: { mode, phone: null, client_number: null, status: 'finalizada', ended_reason: 'completed', error: '',
    duration_seconds: dur, latency: null, created_at: at(m0, 0), started_at: at(m0, 1), ended_at: at(m0, dur) },
});
const F = (name, description, value, required) => ({ name, description, value, required });
const webFields = [
  F('consulta', 'Qué necesita o pregunta la persona, en una frase.', 'Si abren los lunes y el precio de la docena de empanadas', true),
  F('resuelta', 'Si la persona queda conforme con la respuesta.', true, true),
  F('nombre', 'Nombre y apellido de la persona, para que la contacten.', null, false),
  F('contacto', 'Teléfono o mail para contactarla.', null, false),
];
const summary = (id, mode, outcome, dur, m0, h = 15) => ({
  id, client_id: clientId, client_name: 'El Fogón', agent_id: agentId, agent_name: agentName, agent_version: 2,
  workflow_status: 'completed', created_at: new Date(Date.UTC(2026, 9, 24, h, m0, 0)).toISOString(), contact_name: null, company: null,
  outcome, goal: true, captured: 2, required: 2, mode, phone: null, status: 'finalizada', duration_seconds: dur,
  ended_reason: 'completed', latency_avg: null,
});
let listMode = 'empty';
await page.setRequestInterception(true);
page.on('request', (req) => {
  const u = new URL(req.url());
  const json = (body) => req.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  if (req.method() === 'POST' && u.pathname === '/api/v1/calls')
    return req.respond({ status: 201, contentType: 'application/json', body: JSON.stringify({ conversation_id: FAKE_TEST, room: 'x', mode: 'prueba', join_url: null }) });
  if (req.method() === 'POST' && u.pathname.startsWith('/api/v1/calls')) return req.abort();
  if (req.method() === 'GET' && u.pathname === `/api/v1/calls/${FAKE_TEST}`)
    return json(detail(FAKE_TEST, 'prueba', testMsgs, webFields.map((f) => ({ ...f, value: null })), null, 40, 10));
  if (req.method() === 'GET' && u.pathname === `/api/v1/calls/${FAKE_WEB}`)
    return json(detail(FAKE_WEB, 'web', webMsgs, webFields, { label: 'Consulta resuelta', goal: true }, 58, 32));
  if (req.method() === 'GET' && u.pathname === '/api/v1/calls') {
    if (u.searchParams.get('mode') === 'prueba' || listMode === 'empty') return json({ items: [], total: 0 });
    const items = [
      summary(FAKE_WEB, 'web', 'Consulta resuelta', 58, 32, 18),
      summary('0e0e0e0e-0000-4000-8000-000000000103', 'web', 'Consulta resuelta', 71, 5, 17),
      summary('0e0e0e0e-0000-4000-8000-000000000104', 'web', 'Consulta resuelta', 44, 48, 16),
      summary(FAKE_TEST, 'prueba', 'Consulta resuelta', 40, 10, 15),
    ];
    return json({ items, total: items.length });
  }
  return req.continue();
});

// ---- 1. Inicio y menú ----
await login(page);
const me = await page.evaluate(async () => (await fetch('/api/v1/auth/me')).json());
clientId = me.client_id;
await page.goto(`${base}/`, { waitUntil: 'networkidle0' }); await wait(1200);
await shot('01-inicio');
taps.menu = { x: 30, y: 30 };
await page.click('button[aria-label]').catch(() => {}); await wait(600);
await shot('02-menu');
await tap('agentes', 'Agentes', 'button, a');
await clickText(page, 'Agentes', 'button, a'); await wait(500);
await shot('03-menu-agentes');
await tap('misAgentes', 'Mis agentes', 'a');
await page.goto(`${base}/agents`, { waitUntil: 'networkidle0' }); await wait(1000);
await shot('04-agentes');
await tap('nuevo', 'Nuevo agente', 'button');

// ---- 2. Nuevo agente ----
await clickText(page, 'Nuevo agente'); await wait(900);
await shot('05-modal');
await page.type('.mantine-Modal-body input[maxlength="128"]', 'Atención El Fogón', { delay: 20 });
await page.type('.mantine-Modal-body textarea', 'Menú, precios y horarios');
await wait(400);
await shot('06-modal-nombre');
await tap('crear', 'Crear agente', 'button[type=submit]');
await clickText(page, 'Crear agente', 'button[type=submit]');
await wait(2200);
agentId = page.url().split('/agents/')[1].split('?')[0];
agentName = 'Atención El Fogón';
await shot('07-def');

// ---- 3. Definición: rol y base de conocimiento ----
const setField = async (sel, text, step) => {
  await page.evaluate((sel) => { const el = document.querySelector(sel); el.scrollIntoView({ block: 'center' }); el.focus(); el.select?.(); }, sel);
  await page.keyboard.down('Control'); await page.keyboard.press('a'); await page.keyboard.up('Control');
  await page.keyboard.press('Backspace');
  await page.type(sel, text, { delay: 2 });
};
const rolSel = 'input[placeholder="recepcionista virtual de la Clínica del Sol"]';
await page.evaluate((s) => document.querySelector(s).scrollIntoView({ block: 'center' }), rolSel); await wait(400);
await shot('08-rol-antes');
await setField(rolSel, 'asistente virtual de la parrilla El Fogón');
await page.evaluate(() => document.activeElement.blur());
await wait(300);
await shot('09-rol');
const kbSel = 'textarea[aria-label="Base de conocimiento"]';
const KB = [
  '- El Fogón: parrilla en Palermo. Abre de martes a domingo, al mediodía y a la noche; los lunes, cerrado.',
  '- Parrillada para dos: $ 38.000.',
  '- Menú del día, con bebida: $ 14.000.',
  '- Empanadas, la docena: $ 18.000.',
];
await page.evaluate((s) => { const el = document.querySelector(s); el.scrollIntoView({ block: 'start' }); window.scrollBy(0, -150); }, kbSel); await wait(400);
await shot('10-kb-antes');
await page.evaluate((s) => document.querySelector(s).focus(), kbSel);
await page.keyboard.down('Control'); await page.keyboard.press('a'); await page.keyboard.up('Control');
await page.keyboard.press('Backspace');
for (let i = 0; i < KB.length; i++) {
  await page.type(kbSel, (i ? '\n' : '') + KB[i], { delay: 1 });
  await wait(200);
  await page.evaluate((s) => { const el = document.querySelector(s); el.scrollIntoView({ block: 'start' }); window.scrollBy(0, -150); }, kbSel);
  await wait(250);
  await shot(`11-kb-${i + 1}`);
}
taps.kb = await page.evaluate((s) => { const r = document.querySelector(s).getBoundingClientRect(); return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + 30) }; }, kbSel);
await page.evaluate(() => document.activeElement.blur());
await page.evaluate(() => document.querySelector('.def-toolbar').scrollIntoView({ block: 'start' }));
await page.evaluate(() => window.scrollBy(0, -90)); await wait(400);
await shot('12-guardar');
await tap('guardar', 'Guardar versión nueva', 'button');
await clickText(page, 'Guardar versión nueva', 'button'); await wait(1600);
await shot('13-guardado');

// ---- 4. Probar ----
await page.goto(`${base}/agents/${agentId}?tab=probar`, { waitUntil: 'networkidle0' }); await wait(1200);
await shot('14-probar-tab');
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find((x) => x.textContent.trim() === 'Probar agente'); b.scrollIntoView({ block: 'center' }); window.scrollBy(0, 120); }); await wait(500);
await shot('15-probar-voz');
await tap('probarAgente', 'Probar agente', 'button');
await clickText(page, 'Probar agente', 'button'); await wait(3000);
// La página de la llamada: el detalle (mock) está finalizado; se pasa el estado a "en llamada" y el agente hablando.
const setTestState = () => page.evaluate(() => {
  const el = [...document.querySelectorAll('h4')].find((x) => x.textContent.includes('Conversación')) ?? document.querySelector('main');
  const key = Object.keys(el).find((k) => k.startsWith('__reactFiber'));
  let f = el[key];
  while (f) {
    let h = f.memoizedState, hooks = [];
    while (h && typeof h === 'object' && 'next' in h) { hooks.push(h); h = h.next; }
    const i = hooks.findIndex((x) => x.memoizedState === 'ended' && x.queue);
    if (i >= 0) { hooks[i].queue.dispatch('live'); hooks[i + 4].queue.dispatch(true); return true; }
    f = f.return;
  }
  return false;
});
console.log('test live', await setTestState()); await wait(800);
await shot('16-llamada-prueba');
await page.evaluate(() => { const h = [...document.querySelectorAll('h4')].find((x) => x.textContent.includes('Conversación')); h?.scrollIntoView({ block: 'start' }); window.scrollBy(0, -80); }); await wait(400);
await shot('17-llamada-prueba-chat');

// ---- 5. Link para llamar ----
await page.goto(`${base}/agents/${agentId}?tab=link`, { waitUntil: 'networkidle0' }); await wait(1200);
await shot('18-link-vacio');
await tap('crearLink', 'Crear link', 'button');
await clickText(page, 'Crear link', 'button'); await wait(1500);
await shot('19-link-creado');
await page.evaluate(() => document.querySelector('.mantine-Notification-root, .mantine-Notifications-notification')?.remove()); 
await tap('copiar', 'Copiar link', 'button');
await page.evaluate(() => { const b = document.querySelector('button[aria-label="Copiar link"]'); b?.click(); b?.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); });
await page.hover('button[aria-label="Copiar link"]').catch(() => {});
await wait(500);
await shot('20-link-copiado');
const link = await page.evaluate(async (id) => (await fetch(`/api/v1/agents/${id}/call-link`)).json(), agentId);
const token = link.link?.token ?? link.link?.url?.split('/').pop();
console.log('link', link.link?.url);

// ---- 6. La página pública del link (la que abre el cliente), en otra pestaña ----
const mainPage = page;
page = await browser.newPage();
await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await page.goto(`http://127.0.0.1:8113/llamar/${token}`, { waitUntil: 'networkidle0' }).catch((e) => console.log(e.message)); await wait(1500);
await page.evaluate(() => document.getElementById('turnstile')?.remove());
await shot('21-llamar');
taps.llamar = await page.evaluate(() => { const r = document.querySelector('[data-call]')?.getBoundingClientRect(); return r ? { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) } : null; });
await page.evaluate((lines) => {
  const phone = document.querySelector('.phone');
  phone.dataset.state = 'live';
  document.querySelector('[data-status]').textContent = 'En llamada';
  document.querySelectorAll('[data-group]').forEach((el) => { el.hidden = el.dataset.group !== 'call'; });
  const timer = document.querySelector('[data-timer]'); timer.hidden = false; timer.textContent = '00:24';
  document.querySelector('[data-hint]').textContent = 'Sofía habla…';
  document.querySelector('[data-mute]').disabled = false;
  const tg = document.querySelector('[data-captions-toggle]'); tg.hidden = false; tg.textContent = 'Ocultar subtítulos'; tg.setAttribute('aria-expanded', 'true');
  const cap = document.querySelector('[data-captions]'); cap.hidden = false; cap.replaceChildren();
  for (const [who, t] of lines) { const p = document.createElement('p'); const b = document.createElement('b'); b.textContent = who + ': '; p.append(b, document.createTextNode(t)); cap.append(p); }
  phone.style.setProperty('--level', '0.6');
}, [['Sofía', 'Hola, gracias por comunicarte. Te habla Sofía, la asistente virtual. ¿En qué te puedo ayudar?'], ['Vos', 'Hola, ¿abren los lunes?'], ['Sofía', 'Los lunes está cerrado. Abrimos de martes a domingo, al mediodía y a la noche.']]);
await wait(500);
await shot('22-llamar-en-llamada');

// ---- 7. Conversaciones ----
page.on('dialog', (d) => d.accept());
await page.close().catch(() => {});
page = mainPage;
listMode = 'full';
await page.goto(`${base}/calls`, { waitUntil: 'domcontentloaded' }); await wait(3000);
await shot('23-conversaciones');
taps.conv = await page.evaluate((id) => { const a = document.querySelector(`a[href$="${id}"]`) ?? [...document.querySelectorAll('tbody tr')][0]; const r = a?.getBoundingClientRect(); return r ? { x: Math.round(r.x + Math.min(r.width, 300) / 2), y: Math.round(r.y + r.height / 2) } : null; }, FAKE_WEB);
await page.goto(`${base}/calls/${FAKE_WEB}`, { waitUntil: 'domcontentloaded' }); await wait(3500);
await shot('24-detalle');
await page.evaluate(() => { const h = [...document.querySelectorAll('h4')].find((x) => /Conversación|Transcripción/.test(x.textContent)); h?.scrollIntoView({ block: 'start' }); window.scrollBy(0, -80); }); await wait(400);
await shot('25-detalle-chat');

// ---- 8. El plan: candados, Equipo y planes ----
await page.goto(`${base}/`, { waitUntil: 'domcontentloaded' }); await wait(2500);
await page.click('button[aria-label]').catch(() => {}); await wait(500);
await clickText(page, 'Organización', 'button, a'); await wait(300);
await clickText(page, 'Cuenta', 'button, a'); await wait(500);
await shot('26-menu-plan');
await tap('equipo', 'Equipo', 'a');
await page.goto(`${base}/team`, { waitUntil: 'domcontentloaded' }); await wait(2500);
await shot('27-equipo');
await tap('mejorar', 'Mejorar mi plan', 'a, button');
await page.goto(`${base}/plan`, { waitUntil: 'domcontentloaded' }); await wait(2500);
await page.evaluate(() => { const h = [...document.querySelectorAll('h4, h3')].find((x) => x.textContent.trim() === 'Planes'); h?.scrollIntoView({ block: 'start' }); window.scrollBy(0, -80); }); await wait(400);
await shot('28-planes');
fs.writeFileSync(`${out}/taps.json`, JSON.stringify(taps, null, 2));
await browser.close();

import { abrir, login, clickText, wait, base, out, inicio, sinSpell } from './ll_lib.mjs';
let { browser, page } = await abrir();
await inicio(page);
await clickText(page, 'Teléfono del equipo', 'a'); await wait(1500);
console.log('juan', await page.evaluate(() => {
  const el = [...document.querySelectorAll('[role=list] *')].find((e) => e.children.length === 0 && e.textContent.trim() === 'Juan Pérez');
  (el.closest('button, [role=listitem], a') ?? el).click(); return !!el; }));
await wait(1200); await page.mouse.move(1000, 950);
await page.screenshot({ path: `${out}/09-telefono.png` });
await browser.close();
// App del teléfono (celular)
({ browser, page } = await abrir(390, 844, 2));
await page.goto(`${base}/login`, { waitUntil: 'networkidle0' });
await page.type('input[type=email]', 'dev@miempresa.example'); await page.type('input[type=password]', 'clave-demo-123');
await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {}), page.click('button[type=submit]')]);
await wait(1000);
await page.goto(`${base}/telefono.html`, { waitUntil: 'networkidle0' }); await wait(1500);
await page.screenshot({ path: `${out}/10-app-recientes.png` });
console.log('contactos', await clickText(page, 'Contactos', 'button, a, [role=tab]')); await wait(1000);
await page.screenshot({ path: `${out}/11-app-contactos.png` });
console.log('juan', await page.evaluate(() => { const el = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && e.textContent.trim() === 'Juan Pérez'); (el.closest('button, a, li, [role]') ?? el).click(); return !!el; }));
await wait(1000);
await page.screenshot({ path: `${out}/12-app-ficha.png` });
await browser.close();

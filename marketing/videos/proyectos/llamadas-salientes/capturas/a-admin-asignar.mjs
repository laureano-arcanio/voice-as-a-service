import { abrir, login, clickText, wait, base, out } from './ll_lib.mjs';
const { browser, page } = await abrir();
await login(page, 'admin@oime.com.ar', 'admin12345');
await page.goto(`${base}/admin/numbers`, { waitUntil: 'networkidle0' }); await wait(1000);
await page.screenshot({ path: `${out}/01-admin-numeros.png` });
console.log('asignar', await clickText(page, 'Asignar', 'button, a'));
await wait(900);
await page.screenshot({ path: `${out}/02a-asignar-modal.png` });
// elegir el cliente
await page.click('[role=dialog] input'); await wait(500);
console.log('cliente', await clickText(page, 'Mi Empresa', '[role=option]'));
await wait(600);
await page.screenshot({ path: `${out}/02-asignar.png` });
console.log('ok', await clickText(page, 'Asignar', '[role=dialog] button'));
await wait(1500);
await page.screenshot({ path: `${out}/02b-asignado.png` });
await browser.close();

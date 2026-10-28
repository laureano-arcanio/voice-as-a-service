import { abrir, login, clickText, wait, base, out } from './ll_lib.mjs';
const { browser, page } = await abrir(390, 844, 2);
await page.goto(`${base}/login`, { waitUntil: 'networkidle0' });
await page.type('input[type=email]', 'dev@miempresa.example'); await page.type('input[type=password]', 'clave-demo-123');
await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {}), page.click('button[type=submit]')]);
for (const [ph, name] of [['ringing', '13-app-sonando'], ['active', '14-app-llamada']]) {
  await page.goto(`${base}/zz-captura-tmp.html?phase=${ph}`, { waitUntil: 'networkidle0' }); await wait(1200);
  await page.screenshot({ path: `${out}/${name}.png` });
}
await browser.close();

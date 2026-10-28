import { abrir, clickText, wait, base, out, inicio } from './ll_lib.mjs';
const { browser, page } = await abrir();
await inicio(page);
await page.goto(`${base}/account`, { waitUntil: 'networkidle0' }); await wait(1000); await page.mouse.move(900, 950);
await page.screenshot({ path: `${out}/06b-numero-guardado.png` });
await page.goto(`${base}/team`, { waitUntil: 'networkidle0' }); await wait(1000); await page.mouse.move(900, 950);
await page.screenshot({ path: `${out}/05-equipo-lista.png` });
await browser.close();

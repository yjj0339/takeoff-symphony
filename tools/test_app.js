/* 整场演出截图（浏览器级 page.screenshot，走 __app 钩子） */
const pw = require('C:/Users/HUAWEI/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = 'C:/Users/HUAWEI/.agent-browser/browsers/chrome-150.0.7871.115/chrome.exe';
const fs = require('fs');
(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--disable-gpu-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  const times = [4, 20, 58, 75, 90, 100, 115, 130, 150];
  await page.goto('http://127.0.0.1:5177/?mode=shot', { waitUntil: 'load' });
  await page.waitForFunction('!!window.__app', { timeout: 40000 });
  await page.waitForTimeout(1000);
  fs.mkdirSync('shots', { recursive: true });
  for (const tt of times) {
    await page.evaluate((t) => {
      document.body.classList.add('playing');
      document.getElementById('cover').classList.add('off');
      window.__app.seek(t);
      for (let k = 0; k < 6; k++) window.__app.frameAt(t, 0.45);
    }, tt);
    await page.waitForTimeout(260);
    await page.screenshot({ path: `shots/app_t${tt}.png` });
    console.log('shot t=' + tt);
  }
  console.log('ERRORS:', errs.length ? errs.join(' | ') : 'none');
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });

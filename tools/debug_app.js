const pw = require('C:/Users/HUAWEI/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = 'C:/Users/HUAWEI/.agent-browser/browsers/chrome-150.0.7871.115/chrome.exe';
(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--disable-gpu-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  page.on('console', m => console.log('[' + m.type() + ']', m.text().slice(0, 200)));
  page.on('response', r => { if (r.status() >= 400) console.log('HTTP', r.status(), r.url()); });
  await page.goto('http://127.0.0.1:5177/?shots=4,20&now=1', { waitUntil: 'load' });
  await page.waitForTimeout(8000);
  const st = await page.evaluate(() => ({ done: window.__shotsDone, shots: (window.__shots||[]).length, ready: !!window.__plane }));
  console.log('STATE:', JSON.stringify(st));
  await browser.close();
})();

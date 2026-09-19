/* 模型验证截图（静默 headless） */
const pw = require('C:/Users/HUAWEI/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = 'C:/Users/HUAWEI/.agent-browser/browsers/chrome-150.0.7871.115/chrome.exe';
const fs = require('fs');
(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--disable-gpu-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text()); });
  const views = ['threeq', 'sideR', 'sideL', 'rear', 'engineR', 'noseR', 'gearN', 'gearMR', 'textR', 'textL', 'finR', 'finL'];
  fs.mkdirSync('shots', { recursive: true });
  await page.goto(`http://127.0.0.1:5177/test_model.html?view=threeq`, { waitUntil: 'load' });
  await page.waitForFunction('window.__ready === true', { timeout: 20000 });
  await page.waitForTimeout(900);
  for (const v of views) {
    await page.evaluate((n) => window.__setView(n), v);
    await page.waitForTimeout(500);
    await page.screenshot({ path: `shots/model_${v}.png` });
    console.log('shot', v);
  }
  const dump = await page.evaluate(() => window.__dump());
  console.log('DUMP:', JSON.stringify(dump, null, 1));
  console.log('ERRORS:', errors.length ? errors.join('\n') : 'none');
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });

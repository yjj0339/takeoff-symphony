const pw = require('C:/Users/HUAWEI/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = 'C:/Users/HUAWEI/.agent-browser/browsers/chrome-150.0.7871.115/chrome.exe';
(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--disable-gpu-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  await page.goto('http://127.0.0.1:5177/test_scene.html?view=apron', { waitUntil: 'load' });
  await page.waitForFunction('window.__ready === true', { timeout: 30000 });
  await page.waitForTimeout(800);
  for (const v of ['apron', 'lineup', 'tower', 'aerial']) {
    await page.evaluate((n) => window.__setView(n), v);
    await page.waitForTimeout(500);
    await page.screenshot({ path: `shots/scene_${v}.png` });
    console.log('shot', v);
  }
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });

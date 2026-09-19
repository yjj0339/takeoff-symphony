const pw = require('C:/Users/HUAWEI/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = 'C:/Users/HUAWEI/.agent-browser/browsers/chrome-150.0.7871.115/chrome.exe';
(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--disable-gpu-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148' });
  const page = await ctx.newPage();
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  await page.goto('http://127.0.0.1:5177/', { waitUntil: 'load' });
  await page.waitForFunction('!!window.__app', { timeout: 40000 });
  await page.waitForTimeout(900);
  await page.screenshot({ path: 'shots/m_cover.png' });
  await page.click('#btnStart');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: 'shots/m_t2.png' });
  for (const tt of [75, 115]) {
    await page.evaluate((t) => { window.__app.seek(t); for (let k = 0; k < 8; k++) window.__app.frameAt(t, 0.4); }, tt);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `shots/m_t${tt}.png` });
  }
  console.log('mobile shots done');
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });

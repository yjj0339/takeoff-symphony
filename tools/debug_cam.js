const pw = require('C:/Users/HUAWEI/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = 'C:/Users/HUAWEI/.agent-browser/browsers/chrome-150.0.7871.115/chrome.exe';
(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true,
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--disable-gpu-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 760 } });
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  await page.goto('http://127.0.0.1:5177/', { waitUntil: 'load' });
  await page.waitForFunction('!!window.__app', { timeout: 40000 });
  await page.waitForTimeout(400);
  for (const t of [100, 115, 150]) {
    const out = await page.evaluate((tt) => {
      document.body.classList.add('playing');
      document.getElementById('cover').classList.add('off');
      const app = window.__app;
      app.seek(tt);
      for (let k = 0; k < 8; k++) app.frameAt(tt, 0.4);
      const cam = app.camera;
      const plane = app.scene.children.find(c => c.type === 'Group' && c.children.length > 20);
      let planePos = null;
      app.scene.traverse(o => { if (o.name === 'Aircraft' && !planePos) planePos = o.position.toArray().map(v => +v.toFixed(1)); });
      return {
        camPos: cam.position.toArray().map(v => +v.toFixed(1)),
        fov: +cam.fov.toFixed(1),
        planePos,
        veil: document.getElementById('cloudVeil').style.opacity,
      };
    }, t);
    console.log('t=' + t, JSON.stringify(out));
  }
  await browser.close();
})();

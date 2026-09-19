/* 凌云起飞 · 静默截图钩子
   用法: index.html?shots=8,30,60,90,120&now=1
   加载后自动逐时刻 seek → 渲染 → canvas.toDataURL 存入 window.__shots
   完成后置 window.__shotsDone = true（playwright 等待此标记）
*/
export function parseShotMode() {
  const q = new URLSearchParams(location.search);
  if (!q.get('shots')) return null;
  return {
    times: q.get('shots').split(',').map(Number).filter(n => !isNaN(n)),
    immediate: q.get('now') === '1',
  };
}

export async function runShotMode(app, times) {
  window.__shots = [];
  const prevT = app.t;
  // 热身：首帧 toDataURL 会读到空 buffer，先丢弃一帧
  app.frameAt(prevT, 0.016);
  void app.renderer.domElement.toDataURL('image/png');
  await new Promise(r => setTimeout(r, 120));
  for (const tt of times) {
    app.seek(tt);
    // 多步推进让相机 damp / HUD 过渡到位
    for (let k = 0; k < 3; k++) {
      app.frameAt(tt, 0.45);
      await new Promise(r => setTimeout(r, 160));
    }
    app.frameAt(tt, 0.05);
    void app.renderer.domElement.toDataURL('image/png');   // 预读强制换 buffer
    await new Promise(r => setTimeout(r, 90));
    app.frameAt(tt, 0.05);
    window.__shots.push({ t: tt, data: app.renderer.domElement.toDataURL('image/png') });
  }
  app.seek(prevT);
  window.__shotsDone = true;
  document.title = 'SHOT_DONE';
}

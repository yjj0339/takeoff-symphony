/* 凌云起飞 · 主入口 */
import * as THREE from 'three';
import { buildEnvironment } from './environment.js';
import { loadPlane } from './plane.js';
import { evalState, DURATION } from './flight.js';
import { Director, MANUAL_SEQ } from './cameras.js';
import { EngineAudio } from './audio.js';
import { initHUD } from './hud.js';
import { parseShotMode, runShotMode } from './shot.js';

const canvas = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.5, 9000);
camera.position.set(196, 26, -880);

const env = buildEnvironment(scene, renderer);
const audio = new EngineAudio();

// ---- 加载 ----
const loading = { airport: false, plane: false };
const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
new GLTFLoader().load('assets/airport.glb', g => { scene.add(g.scene); loading.airport = true; ready(); });
const plane = await loadPlane(scene);
loading.plane = true; ready();

const director = new Director(camera, canvas);
const hud = initHUD({ onSeek: null });

// ---- 状态 ----
const app = {
  t: 0, playing: false, ended: false,
  renderer, scene, camera,
  seek(tt) { this.t = Math.max(0, Math.min(DURATION, tt)); this.ended = false; },
  renderOnce() { renderer.render(scene, camera); },
};

let orbit = null;
async function ready() {
  if (!(loading.airport && loading.plane)) return;
  const q = new URLSearchParams(location.search);
  const shotMode = parseShotMode();

  // OrbitControls（自由视角用，惰性创建）
  const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
  orbit = new OrbitControls(camera, canvas);
  orbit.enableDamping = true; orbit.dampingFactor = 0.08;
  orbit.maxPolarAngle = Math.PI * 0.495;
  orbit.minDistance = 8; orbit.maxDistance = 2600;
  orbit.enabled = false;
  director.attachOrbit(orbit);

  if (shotMode) {
    // 静默截图模式：无封面直跑（HUD 可见）
    document.getElementById('cover').classList.add('off');
    document.body.classList.add('playing');
    await runShotMode(app, shotMode.times);
    return;
  }

  // ---- 封面开始 ----
  document.getElementById('btnStart').addEventListener('click', async () => {
    document.getElementById('cover').classList.add('off');
    document.body.classList.add('playing');
    try { await audio.start(); } catch (e) { /* 无声环境下继续 */ }
    app.playing = true;
    hud.setPlaying(true);
    hud.toast('凌云航空 B-2026 · 起飞全程 ' + Math.round(DURATION) + ' 秒');
  });

  // ---- 控制 ----
  document.getElementById('btnPlay').onclick = () => {
    if (app.ended) { app.seek(0); app.playing = true; app.ended = false; hud.setPlaying(true); return; }
    app.playing = !app.playing;
    hud.setPlaying(app.playing);
  };
  document.getElementById('btnReplay').onclick = () => {
    app.seek(0); app.playing = true; app.ended = false;
    hud.setPlaying(true); hud.toast('重新起飞');
  };
  document.getElementById('btnSound').onclick = (e) => {
    const btn = e.currentTarget;
    audio.setMuted(!audio.muted);
    btn.textContent = audio.muted ? '🔇' : '🔊';
    btn.classList.toggle('on', !audio.muted);
  };
  document.getElementById('btnSound').classList.add('on');
  document.getElementById('btnCam').onclick = (e) => {
    if (director.mode === 'free') { orbit.enabled = false; }
    const label = director.cycleManual();
    hud.setCam('机位 · ' + label);
    hud.toast('机位：' + label);
    e.currentTarget.classList.add('on');
    document.getElementById('btnFree').classList.remove('on');
  };
  document.getElementById('btnFree').onclick = (e) => {
    const btn = e.currentTarget;
    if (director.mode === 'free') {
      director.setMode('auto'); orbit.enabled = false;
      btn.classList.remove('on'); hud.setCam('自动导播');
    } else {
      director.setMode('free'); orbit.enabled = true;
      btn.classList.add('on'); hud.setCam('自由视角 · 拖动旋转');
    }
  };
  hud.onProgress(t => { app.seek(t); });

  // ---- 预渲染首帧（封面底下就有画面）----
  app.frameAt(0, 0.016);
  startLoop();
}

// ---- 渲染一帧（主循环与截图模式共用）----
function frameAt(t, dt) {
  const st = evalState(t);
  plane.update(st, dt, t);
  director.update(t, st, dt);
  if (director.mode === 'free' && orbit) orbit.update();
  audio.update(st);
  env.update(t);
  document.getElementById('cloudVeil').style.opacity = st.cloudVeil.toFixed(3);
  hud.setPhase(st);
  hud.setData(st);
  hud.setProgress(t);
  renderer.render(scene, camera);
}
app.frameAt = frameAt;
window.__app = app;   // 静默测试钩子：seek + frameAt

// ---- 主循环 ----
function startLoop() {
  const clock = new THREE.Clock();
  let elapsed = 0;
  (function loop() {
    requestAnimationFrame(loop);
    const dt = Math.min(clock.getDelta(), 0.05);
    elapsed += dt;
    if (app.playing && !app.ended) {
      app.t += dt;
      if (app.t >= DURATION) {
        app.t = DURATION; app.playing = false; app.ended = true;
        hud.setPlaying(false);
        hud.toast('已入云端 · 点击 ↺ 再飞一次');
      }
    }
    frameAt(app.t, dt);
  })();
}

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

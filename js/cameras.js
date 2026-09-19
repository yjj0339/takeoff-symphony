/* 凌云起飞 · 导播系统：自动机位 + 手动机位 + 自由视角
   动态机位全部跟随 st.alt（飞机高度），否则爬升后目标出画 */
import * as THREE from 'three';

const V3 = (x, y, z) => new THREE.Vector3(x, y, z);
// 飞机参考点（含 5.68 机身轴心离地）
const planeY = s => 5.68 + s.alt;

// ---- 自动导播时间表 ----
const AUTO = [
  [0,   'apronWide'],
  [7,   'bridge'],
  [12,  'taxiFront'],
  [22,  'towerZoom'],
  [34,  'taxiSide'],
  [49,  'turnGround'],
  [56,  'noseClose'],
  [63,  'rearPush'],
  [70,  'sideChase'],
  [84,  'runwayLow'],
  [92.5,'liftChase'],
  [98,  'gearWatch'],
  [108, 'cloudChase'],
  [122, 'bankWide'],
  [140, 'farewell'],
];

// ---- 机位实现：返回 {pos, look, fov} ----
const CAMS = {
  apronWide:  { label: '停机坪全景', get: (t, s) => ({ pos: V3(198, 27, -878), look: V3(143, 7, -950), fov: 32 }) },
  bridge:     { label: '廊桥视角',   get: (t, s) => ({ pos: V3(178, 9.5, -984), look: V3(143, 6.5, -950), fov: 38 }) },
  taxiFront:  { label: '滑行正前',   get: (t, s) => ({ pos: V3(s.x, 2.6, s.z - 58), look: V3(s.x, 7.6, s.z - 16), fov: 40 }) },
  towerZoom:  { label: '塔台长焦',   get: (t, s) => ({ pos: V3(230, 42, -772), look: V3(s.x, planeY(s), s.z), fov: 15 }) },
  taxiSide:   { label: '滑行侧跟',   get: (t, s) => ({ pos: V3(s.x + 64, 9, s.z + 26), look: V3(s.x, planeY(s) + 1, s.z), fov: 32 }) },
  turnGround: { label: '联络道视角', get: (t, s) => ({ pos: V3(58, 2.6, -1140), look: V3(s.x, planeY(s) + 1, s.z - 2), fov: 44 }) },
  noseClose:  { label: '机头特写',   get: (t, s) => ({ pos: V3(s.x, planeY(s) + 0.6, s.z - 48), look: V3(s.x, planeY(s) + 2.4, s.z - 20), fov: 38 }) },
  rearPush:   { label: '机尾推力',   get: (t, s) => ({ pos: V3(s.x - 26, planeY(s) + 1.5, s.z + 70), look: V3(s.x, planeY(s) + 2, s.z + 8), fov: 40 }) },
  sideChase:  { label: '侧翼追踪',   get: (t, s) => ({ pos: V3(s.x + 78, planeY(s) + 4, s.z + 6), look: V3(s.x, planeY(s) + 3, s.z), fov: 34 }) },
  runwayLow:  { label: '跑道仰拍',   get: (t, s) => ({ pos: V3(34, 1.2, 96), look: V3(2, Math.max(9, s.alt * 0.4), s.z), fov: 30 }) },
  liftChase:  { label: '离地追踪',   get: (t, s) => ({ pos: V3(s.x - 98, planeY(s) + 9, s.z + 122), look: V3(s.x, planeY(s) + 4, s.z), fov: 36 }) },
  gearWatch:  { label: '起落架观察', get: (t, s) => ({ pos: V3(s.x - 36, planeY(s) - 2, s.z + 52), look: V3(s.x, planeY(s) + 5, s.z - 6), fov: 38 }) },
  cloudChase: { label: '穿云视角',   get: (t, s) => ({ pos: V3(s.x - 98, planeY(s) + 9, s.z + 115), look: V3(s.x, planeY(s) + 6, s.z), fov: 38 }) },
  bankWide:   { label: '转弯远景',   get: (t, s) => ({ pos: V3(s.x + 190, planeY(s) + 48, s.z - 230), look: V3(s.x, planeY(s) + 12, s.z), fov: 32 }) },
  farewell:   { label: '云上远眺',   get: (t, s) => ({ pos: V3(s.x - 158, planeY(s) + 34, s.z - 126), look: V3(s.x, planeY(s) + 16, s.z), fov: 30 }) },
  // ---- 手动机位 ----
  cockpit:    { label: '驾驶舱视角', get: (t, s) => ({
      pos: V3(s.x + Math.sin(s.hdg + Math.PI) * 27, planeY(s) + 2.4, s.z + Math.cos(s.hdg + Math.PI) * 27),
      look: V3(s.x - Math.sin(s.hdg) * 120, planeY(s) + 2.4 - s.pitch * 320, s.z - Math.cos(s.hdg) * 120), fov: 60 }) },
  cabin:      { label: '客舱翼窗',   get: (t, s) => ({ pos: V3(s.x + 4.6, planeY(s) + 1.4, s.z + 6), look: V3(s.x + 30, planeY(s) + 0.6, s.z - 16), fov: 55 }) },
  towerAll:   { label: '塔台全景',   get: (t, s) => ({ pos: V3(230, 44, -772), look: V3(s.x, planeY(s), s.z), fov: 28 }) },
  topDown:    { label: '上帝视角',   get: (t, s) => ({ pos: V3(s.x + 10, planeY(s) + 120, s.z + 5), look: V3(s.x, planeY(s), s.z), fov: 42 }) },
};

export const MANUAL_SEQ = ['apronWide', 'towerAll', 'sideChase', 'noseClose', 'cockpit', 'cabin', 'gearWatch', 'topDown'];

export class Director {
  constructor(camera, dom) {
    this.cam = camera;
    this.dom = dom;
    this.mode = 'auto';           // auto | manual | free
    this.manualIdx = 0;
    this.cur = { pos: V3(198, 27, -878), look: V3(143, 7, -950), fov: 32 };
    this.orbit = null;
    this.label = '自动导播';
  }
  attachOrbit(orbit) { this.orbit = orbit; }

  setMode(mode, idx) {
    this.mode = mode;
    if (mode === 'manual' && idx !== undefined) this.manualIdx = idx;
    if (mode === 'free' && this.orbit) {
      const c = this.cur;
      this.cam.position.copy(c.pos);
      this.orbit.target.copy(c.look);
      this.orbit.update();
    }
  }
  cycleManual() {
    this.setMode('manual', (this.manualIdx + 1) % MANUAL_SEQ.length);
    return CAMS[MANUAL_SEQ[this.manualIdx]].label;
  }

  autoCamAt(t) {
    let name = AUTO[0][1];
    for (const [t0, n] of AUTO) if (t >= t0) name = n;
    return name;
  }

  update(t, st, dt) {
    if (this.mode === 'free') { this.label = '自由视角'; return; }
    let cam;
    if (this.mode === 'auto') {
      const name = this.autoCamAt(t);
      cam = CAMS[name]; this.label = cam.label;
    } else {
      cam = CAMS[MANUAL_SEQ[this.manualIdx]] || CAMS.sideChase; this.label = cam.label;
    }
    const goal = cam.get(t, st);
    const l = 1 - Math.exp(-3.2 * dt);
    this.cur.pos.lerp(goal.pos, l);
    this.cur.look.lerp(goal.look, l);
    this.cur.fov += (goal.fov - this.cur.fov) * l;
    this.cam.position.copy(this.cur.pos);
    this.cam.lookAt(this.cur.look);
    if (Math.abs(this.cam.fov - this.cur.fov) > 0.05) {
      this.cam.fov = this.cur.fov; this.cam.updateProjectionMatrix();
    }
  }
}

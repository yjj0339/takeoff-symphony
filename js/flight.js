/* 凌云起飞 · 起飞全程时间线（18 号跑道 · 北端进入 · 向南起飞）
   evalState(t) 为纯函数：任意时刻可取完整状态（支持进度条拖动）
   路线：停机位(143,-950,朝北) → 左掉头经西上滑行道 → B0 联络 → 对正(0,-1090) → 加速滑跑 → 抬轮 → 离地爬升 → 穿云 → 左转 → 云上巡航
*/
import * as THREE from 'three';

export const DURATION = 155;

// ---- 地面路径（t, x, z, heading rad）----
const PATH = [
  [0,   143, -950, 0],
  [12,  143, -910, 0],
  [22,  143, -1000, 0],
  [34,  143, -1100, 0],
  [40,  120, -1123, Math.PI * 0.32],
  [46,  84,  -1131, Math.PI * 0.62],
  [52,  16,  -1129, Math.PI * 0.96],
  [56,  0,   -1102, Math.PI],
  [62,  0,   -1064, Math.PI],
  [70,  0,   -620,  Math.PI],
  [78,  0,   -180,  Math.PI],
  [84,  0,   128,   Math.PI],
  [88,  0,   366,   Math.PI],
  [96,  2,   700,   Math.PI],
  [104, 8,   1040,  Math.PI],
  [113, 20,  1420,  Math.PI],
  [122, 38,  1770,  Math.PI],
  [131, 74,  2110,  Math.PI - 0.42],
  [140, 132, 2400,  Math.PI - 0.75],
  [148, 196, 2640,  Math.PI - 0.75],
  [155, 268, 2900,  Math.PI - 0.75],
];

// ---- 标量关键帧 ----
const K = {
  n1:      [[0, .22], [12, .3], [40, .28], [56, .24], [63, .5], [67, 1], [96, 1], [122, .98], [140, .86], [155, .82]],
  spd:     [[0, 0], [12, 5], [34, 10], [50, 7], [56, 0], [63, 8], [70, 33], [78, 55], [84, 71], [88, 82], [91, 88], [96, 97], [104, 106], [113, 113], [122, 120], [140, 130], [155, 136]],
  alt:     [[0, 0], [91, 0], [93, 2.5], [96, 38], [100, 78], [104, 132], [109, 210], [113, 288], [118, 362], [122, 436], [127, 545], [131, 660], [136, 800], [140, 940], [146, 1090], [155, 1240]],
  pitch:   [[0, 0], [84, 0], [87, 0.012], [89, 0.06], [91, 0.115], [93, 0.19], [96, 0.215], [104, 0.235], [113, 0.235], [122, 0.215], [131, 0.17], [140, 0.10], [148, 0.05], [155, 0.04]],
  roll:    [[0, 0], [122, 0], [125, -0.045], [129, -0.23], [136, -0.23], [140, -0.035], [143, 0], [155, 0]],
  hdgExtra:[[122, 0], [126, -0.06], [131, -0.42], [136, -0.72], [140, -0.75], [155, -0.75]],
  gearT:   [[0, 1], [96, 1], [104, 0], [155, 0]],
  flap:    [[0, 0], [50, 0], [55, 1], [110, 1], [119, 0], [155, 0]],
  slat:    [[0, 0], [50, 0], [55, 1], [110, 1], [119, 0], [155, 0]],
  spoiler: [[0, 0], [95, 0], [98, 0.55], [104, 0], [155, 0]],
  steer:   [[0, 0], [36, 0], [40, 0.42], [46, 0.38], [52, -0.30], [57, 0], [155, 0]],
};

export const PHASES = [
  { t: 0,   name: '登机准备', sub: 'BOARDING · 门舱检查' },
  { t: 7,   name: '推出滑出', sub: 'PUSHBACK · 离开廊桥' },
  { t: 12,  name: '地面滑行', sub: 'TAXI · 前往 18 号跑道' },
  { t: 49,  name: '进入联络道', sub: 'TURN · 对正跑道' },
  { t: 56,  name: '起飞前检查', sub: 'LINEUP · 襟翼就位 N1 50%' },
  { t: 63,  name: '起飞滑跑', sub: 'TAKEOFF ROLL · 全推力' },
  { t: 87,  name: '抬轮', sub: 'ROTATE · VR 290 km/h' },
  { t: 91,  name: '离地', sub: 'LIFTOFF · 正上升率' },
  { t: 96,  name: '收起落架', sub: 'GEAR UP · 初始爬升' },
  { t: 108, name: '穿云爬升', sub: 'CLIMB · 通过云底 330m' },
  { t: 122, name: '转弯爬升', sub: 'TURN · 左转航向 135°' },
  { t: 140, name: '云上巡航', sub: 'CRUISE · 凌云之上' },
];

function keys(kf, t) {
  if (t <= kf[0][0]) return kf[0][1];
  for (let i = 0; i < kf.length - 1; i++) {
    const [t0, v0] = kf[i], [t1, v1] = kf[i + 1];
    if (t >= t0 && t <= t1) {
      const u = (t - t0) / (t1 - t0);
      return v0 + (v1 - v0) * smooth(u);
    }
  }
  return kf[kf.length - 1][1];
}
const smooth = u => u * u * (3 - 2 * u);

// Catmull-Rom 路径（按 PATH 段插值）
function pathAt(t) {
  const pts = PATH;
  if (t <= pts[0][0]) return pts[0];
  if (t >= pts[pts.length - 1][0]) return pts[pts.length - 1];
  let i = 0;
  while (i < pts.length - 2 && t > pts[i + 1][0]) i++;
  const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
  const u = (t - p1[0]) / (p2[0] - p1[0]);
  const cr = (a, b, c, d) => b + 0.5 * u * (c - a + u * (2 * a - 5 * b + 4 * c - d + u * (3 * (b - c) + d - a)));
  return [t, cr(p0[1], p1[1], p2[1], p3[1]), cr(p0[2], p1[2], p2[2], p3[2]), keys(HDG, t) + keys(K.hdgExtra, t)];
}
const HDG = PATH.map(p => [p[0], p[3]]);

export function evalState(t) {
  t = Math.max(0, Math.min(DURATION, t));
  const [_, x, z, hdg] = pathAt(t);
  const alt = keys(K.alt, t);
  let phase = PHASES[0], pi = 0;
  for (let i = 0; i < PHASES.length; i++) if (t >= PHASES[i].t) { phase = PHASES[i]; pi = i; }
  return {
    t, x, z, hdg, alt,
    spd: keys(K.spd, t),
    n1: keys(K.n1, t),
    pitch: keys(K.pitch, t),
    roll: keys(K.roll, t),
    gearT: keys(K.gearT, t),
    flap: keys(K.flap, t),
    slat: keys(K.slat, t),
    spoiler: keys(K.spoiler, t),
    steer: keys(K.steer, t),
    onGround: alt < 1.2,
    phase, phaseIndex: pi,
    // 云幕：低云层 330m±55，进入即蒙白
    cloudVeil: THREE.MathUtils.clamp(1 - Math.abs(alt - 330) / 62, 0, 1) * 0.92,
  };
}

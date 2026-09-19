/* 凌云起飞 · 起飞全程时间线（18 号跑道 · 南端进入 · 向北起飞）
   物理一致：地面滑跑段 z(t) 由 v(t) 积分生成（表显速度 == 实际位移速度），
   空中段沿航向积分。任意时刻 evalState(t) 纯函数可求值（进度条拖动）。
   参数：滑跑加速度 3.1 m/s²，VR=82 m/s≈296 km/h，离地 t=92，巡航爬升率 18 m/s
*/
export const DURATION = 155;

const TAXI_T = 63, ROTATE_T = 89.5, LIFT_T = 92, TURN_T0 = 122, TURN_T1 = 140;
const ACCEL = 3.1;
const Z_LINEUP = -1064;

const clamp01 = x => Math.max(0, Math.min(1, x));
const sm = (a, b, x) => { const t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const lerp = (a, b, u) => a + (b - a) * u;

function keys(kf, t) {
  if (t <= kf[0][0]) return kf[0][1];
  for (let i = 0; i < kf.length - 1; i++) {
    const [t0, v0] = kf[i], [t1, v1] = kf[i + 1];
    if (t >= t0 && t <= t1) return lerp(v0, v1, sm(t0, t1, t));
  }
  return kf[kf.length - 1][1];
}

// ---- 滑行段（手铺，到对正停住）----
const TAXI = [
  [0,   143, -950],
  [12,  143, -910],
  [22,  143, -1000],
  [34,  143, -1100],
  [40,  120, -1123],
  [46,  84,  -1131],
  [52,  16,  -1129],
  [56,  0,   -1102],
  [59,  0,   -1067],
  [61,  0,   -1064],
  [63,  0,   -1064],
];
const HDG_TAXI = [[0, 0], [36, 0], [40, Math.PI * 0.32], [46, Math.PI * 0.62], [52, Math.PI * 0.96], [56, Math.PI], [63, Math.PI]];

// ---- 速度函数（表显 == 实际）----
const TAXI_SPD = [[0, 0], [12, 5], [34, 10], [50, 7], [56, 0], [59, 4], [61, 0], [63, 0]];
function vAt(t) {
  if (t < TAXI_T) return keys(TAXI_SPD, t);
  if (t < LIFT_T) return ACCEL * (t - TAXI_T);                       // 滑跑加速
  return 90 + 6 * sm(LIFT_T, LIFT_T + 18, t);                        // 空中 90→96 m/s
}
function hdgAt(t) {
  const turn = t <= TURN_T0 ? 0 : t >= TURN_T1 ? 1 : sm(TURN_T0, TURN_T1, t);
  return Math.PI - 0.75 * turn;                                      // 左转 43°（航向 155°）
}

// ---- 空中段路径表：由 v(t)·hdg(t) 积分 ----
const TABLE = [[TAXI_T, 0, Z_LINEUP]];
{
  let x = 0, z = Z_LINEUP;
  const dt = 0.5;
  for (let t = TAXI_T + dt; t <= DURATION + 0.001; t += dt) {
    const v = vAt(t - dt / 2), h = hdgAt(t - dt / 2);
    x += -Math.sin(h) * v * dt;
    z += -Math.cos(h) * v * dt;
    TABLE.push([t, x, z]);
  }
}
const FULL = [...TAXI, ...TABLE.slice(1)];   // [t, x, z]

function pathXZ(t) {
  if (t <= FULL[0][0]) return [FULL[0][1], FULL[0][2]];
  const last = FULL[FULL.length - 1];
  if (t >= last[0]) return [last[1], last[2]];
  let i = 0;
  while (i < FULL.length - 2 && t > FULL[i + 1][0]) i++;
  const p0 = FULL[Math.max(0, i - 1)], p1 = FULL[i], p2 = FULL[i + 1], p3 = FULL[Math.min(FULL.length - 1, i + 2)];
  const u = (t - p1[0]) / (p2[0] - p1[0]);
  const cr = (a, b, c, d) => b + 0.5 * u * (c - a + u * (2 * a - 5 * b + 4 * c - d + u * (3 * (b - c) + d - a)));
  return [cr(p0[1], p1[1], p2[1], p3[1]), cr(p0[2], p1[2], p2[2], p3[2])];
}

// ---- 标量曲线 ----
const ALT = [[0, 0], [92, 0], [93, 4], [94, 12], [97, 52], [100, 93], [103, 140], [106, 192],
             [112, 300], [118, 408], [124, 516], [130, 624], [136, 732], [142, 840], [148, 948], [155, 1074]];
const PITCH = [[0, 0], [88, 0], [89.5, 0.03], [91, 0.12], [92, 0.185], [95, 0.21], [110, 0.21],
               [122, 0.17], [131, 0.12], [140, 0.09], [150, 0.055], [155, 0.05]];
const ROLL = [[0, 0], [121, 0], [125, -0.07], [129, -0.30], [136, -0.30], [140.5, -0.05], [144, 0], [155, 0]];
const GEAR = [[0, 1], [96, 1], [105, 0], [155, 0]];
const FLAP = [[0, 0], [50, 0], [55, 1], [112, 1], [120, 0], [155, 0]];
const SLAT = [[0, 0], [50, 0], [55, 1], [112, 1], [120, 0], [155, 0]];
const SPOILER = [[0, 0], [155, 0]];
const STEER = [[0, 0], [36, 0], [40, 0.42], [46, 0.38], [52, -0.30], [57, 0], [155, 0]];
const N1 = [[0, .22], [12, .3], [40, .28], [56, .24], [63, .5], [67, 1], [110, 1], [125, .97], [140, .88], [155, .84]];

export const PHASES = [
  { t: 0,   name: '登机准备', sub: 'BOARDING · 门舱检查' },
  { t: 7,   name: '推出滑出', sub: 'PUSHBACK · 离开廊桥' },
  { t: 12,  name: '地面滑行', sub: 'TAXI · 前往跑道' },
  { t: 49,  name: '进入联络道', sub: 'TURN · 对正跑道' },
  { t: 56,  name: '起飞前检查', sub: 'LINEUP · 襟翼就位 N1 50%' },
  { t: 63,  name: '起飞滑跑', sub: 'TAKEOFF ROLL · 全推力' },
  { t: 88,  name: '抬轮', sub: 'ROTATE · VR 296 km/h' },
  { t: 92,  name: '离地', sub: 'LIFTOFF · 正上升率' },
  { t: 97,  name: '收起落架', sub: 'GEAR UP · 初始爬升' },
  { t: 108, name: '穿云爬升', sub: 'CLIMB · 通过云底 330m' },
  { t: 122, name: '转弯爬升', sub: 'TURN · 左转航向 155°' },
  { t: 140, name: '云上巡航', sub: 'CRUISE · 凌云之上' },
];

export function evalState(t) {
  t = Math.max(0, Math.min(DURATION, t));
  const [x, z] = pathXZ(t);
  const hdg = t < TAXI_T ? keys(HDG_TAXI, t) : hdgAt(t);
  const alt = keys(ALT, t);
  let phase = PHASES[0], phaseIndex = 0;
  for (let i = 0; i < PHASES.length; i++) if (t >= PHASES[i].t) { phase = PHASES[i]; phaseIndex = i; }
  return {
    t, x, z, hdg, alt,
    spd: vAt(t),
    n1: keys(N1, t),
    pitch: keys(PITCH, t),
    roll: keys(ROLL, t),
    gearT: keys(GEAR, t),
    flap: keys(FLAP, t),
    slat: keys(SLAT, t),
    spoiler: keys(SPOILER, t),
    steer: keys(STEER, t),
    onGround: alt < 1.2,
    phase, phaseIndex,
    cloudVeil: Math.max(0, Math.min(1, 1 - Math.abs(alt - 330) / 62)) * 0.78,
  };
}

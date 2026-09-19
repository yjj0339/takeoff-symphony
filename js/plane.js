/* 凌云起飞 · 飞机装配与部件联动
   GLB 层级命名（Blender 导出）：
   FanPivotR/L 风扇轴 · Fan 与 FanDisc 高低速切换 · Wheel 开头的为机轮(自转)
   GearNPivot / GearMRPivot / GearMLPivot 收放轴 · DoorNPivot / DoorMPivot 舱门
   FlapPivotIn/Out · SlatPivotIn/Out · SpoilPivot1..5 · NoseSteerPivot · BogieM
*/
import * as THREE from 'three';

export async function loadPlane(scene) {
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
  const gltf = await new GLTFLoader().loadAsync('assets/plane.glb');
  const plane = gltf.scene;
  plane.position.set(0, 5.68, 0);
  plane.rotation.order = 'YXZ';
  scene.add(plane);

  const P = { root: plane };
  plane.traverse(o => { P[o.name] = o; });
  P.fans = [P.FanPivotR, P.FanPivotL].filter(Boolean);
  P.fanMeshes = [P.FanR, P.FanR_1, P.FanR_2, P.FanL, P.FanL_1, P.FanL_2].filter(Boolean);
  P.fanDiscs = [P.FanDiscR, P.FanDiscL].filter(Boolean);
  P.fanDiscs.forEach(d => d.visible = false);
  P.wheels = Object.keys(P).filter(k => /^Wheel(N|MR?L?\d?)/.test(k)).map(k => P[k]);
  P.wheelMeshes = [];
  plane.traverse(o => { if (/^(NoseWheel|MainWheel)/.test(o.name) && o.isMesh) P.wheelMeshes.push(o); });
  P.gearPivots = [P.GearNPivot, P.GearMRPivot, P.GearMLPivot].filter(Boolean);
  P.doorPivots = [P.DoorNPivotL, P.DoorNPivotR, P.DoorMLPivot, P.DoorMRPivot].filter(Boolean);
  P.bogies = [P.BogieMR, P.BogieML].filter(Boolean);
  P.flaps = Object.keys(P).filter(k => /^FlapPivot/.test(k)).map(k => P[k]);
  P.slats = Object.keys(P).filter(k => /^SlatPivot/.test(k)).map(k => P[k]);
  P.spoilers = Object.keys(P).filter(k => /^SpoilPivot/.test(k)).map(k => P[k]);

  // 灯光材质（AircraftLights 的 6 个 primitive：0红闪 1红常 2绿常 3白闪 4暖 5黑）
  P.lightMats = { beacon: null, strobe: null };
  const lightsMesh = P.AircraftLights;
  if (lightsMesh && lightsMesh.isMesh) {
    // 多 primitive 拆成子 mesh：AircraftLights_1..N，材质序即 spec 顺序
    const fam = [];
    plane.traverse(o => { if (/^AircraftLights/.test(o.name) && o.isMesh) fam.push(o); });
    fam.sort((a, b) => (a.name < b.name ? -1 : 1));
    const byMat = {};
    fam.forEach(m => { const src = m.material.userData?.srcIdx ?? m.name; byMat[m.material.uuid] = m.material; });
    // 材质顺序依据 name 后缀：_1=红闪 _2=红常 _3=绿 _4=白 ... 以导出为准：按 userData 难拿，改用 emissive 颜色区分
    const all = Object.values(byMat);
    P.lightMats.beacon = all.find(m => m.emissive && m.emissive.r > 0.5 && m.emissive.g < 0.3 && m.emissive.b < 0.3);
    P.lightMats.strobe = all.find(m => m.emissive && m.emissive.r > 0.6 && m.emissive.g > 0.6);
    P.lightMats.all = all;
  }

  const lerp = THREE.MathUtils.lerp;
  const damp = (a, b, l, dt) => lerp(a, b, 1 - Math.exp(-l * dt));

  let fanSpin = 0, wheelSpin = 0, beaconT = 0, strobeT = 0;

  function update(st, dt, elapsed) {
    // ---- 姿态与位置 ----
    plane.position.set(st.x, 5.68 + st.alt, st.z);
    plane.rotation.y = st.hdg;
    plane.rotation.x = -st.pitch;
    plane.rotation.z = st.roll;

    // ---- 风扇 ----
    const n1 = st.n1;
    fanSpin += (0.6 + n1 * 42) * dt;
    const fast = n1 > 0.52;
    P.fans.forEach(f => f.rotation.z = fanSpin);
    if (P._fast !== fast) {
      P._fast = fast;
      P.fanMeshes.forEach(m => m.visible = !fast);
      P.fanDiscs.forEach(d => d.visible = fast);
    }
    P.fanDiscs.forEach(d => d.rotation.z = -fanSpin * 0.25);

    // ---- 机轮 ----
    if (st.onGround && st.spd > 0.2) wheelSpin -= (st.spd / 0.62) * dt;
    P.wheelMeshes.forEach(m => m.rotation.x = wheelSpin);

    // ---- 起落架收放（down: 1=放下 0=收起）----
    const g = st.gearT;
    const strutAng = (1 - g) * 1.53;                 // ~88°
    P.gearPivots.forEach(p => p.rotation.x = p.name.includes('N') ? -strutAng : strutAng);
    const doorOpen = Math.max(0, 1 - Math.abs(g - 0.5) * 2.6);
    P.doorPivots.forEach(p => {
      if (p.name.includes('N')) p.rotation.y = (p.name.endsWith('L') ? -1 : 1) * doorOpen * 1.25;
      else p.rotation.x = -doorOpen * 1.05;
    });
    // bogie 随俯仰微动
    P.bogies.forEach(b => b.rotation.x = -st.pitch * 0.55);

    // ---- 前轮转向 ----
    if (P.NoseSteerPivot) P.NoseSteerPivot.rotation.y = damp(P.NoseSteerPivot.rotation.y, st.steer, 6, dt);

    // ---- 襟翼 / 缝翼 / 扰流板 ----
    P.flaps.forEach(p => p.rotation.x = damp(p.rotation.x, st.flap * 0.72, 3.2, dt));
    P.slats.forEach(p => p.rotation.x = damp(p.rotation.x, -st.slat * 0.30, 3.2, dt));
    P.spoilers.forEach(p => p.rotation.x = damp(p.rotation.x, -st.spoiler * 0.85, 5, dt));

    // ---- 灯光节奏 ----
    beaconT = (beaconT + dt) % 1.4;
    strobeT = (strobeT + dt) % 1.7;
    const beaconOn = (beaconT < 0.09 || (beaconT > 0.5 && beaconT < 0.59)) ? 1 : 0.06;
    const strobeOn = (strobeT < 0.05 || (strobeT > 0.11 && strobeT < 0.16)) ? 1 : 0.04;
    if (P.lightMats.beacon) P.lightMats.beacon.emissiveIntensity = 2 + beaconOn * 7;
    if (P.lightMats.strobe) P.lightMats.strobe.emissiveIntensity = 1 + strobeOn * 11;
  }

  return { root: plane, P, update };
}

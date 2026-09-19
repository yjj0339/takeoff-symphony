/* 凌云起飞 · 环境：天空穹顶 / 太阳+阴影 / 双层云海 / 雾 / 大地盘 */
import * as THREE from 'three';

export function buildEnvironment(scene, renderer) {
  // ---- 程序环境反射（浅色渐变）----
  const cv = document.createElement('canvas'); cv.width = 64; cv.height = 64;
  const g = cv.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 0, 64);
  grad.addColorStop(0, '#eaf6ff'); grad.addColorStop(0.42, '#cfe8f7');
  grad.addColorStop(0.55, '#c9d8c2'); grad.addColorStop(1, '#b0c0a8');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  const envTex = new THREE.CanvasTexture(cv);
  envTex.mapping = THREE.EquirectangularReflectionMapping;
  envTex.colorSpace = THREE.SRGBColorSpace;
  scene.environment = envTex;

  // ---- 天空穹顶（跟随相机）----
  const skyGeo = new THREE.SphereGeometry(13000, 32, 18);
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: {
      top: { value: new THREE.Color(0x6db9ec) },
      mid: { value: new THREE.Color(0xcfe8f7) },
      hor: { value: new THREE.Color(0xf2f9fd) },
      sunDir: { value: new THREE.Vector3(0.40, 0.48, -0.72).normalize() },
    },
    vertexShader: `
      varying vec3 vDir;
      void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      varying vec3 vDir; uniform vec3 top, mid, hor, sunDir;
      void main() {
        float h = clamp(vDir.y, -0.05, 1.0);
        vec3 col = mix(hor, mid, smoothstep(0.0, 0.18, h));
        col = mix(col, top, smoothstep(0.18, 0.72, h));
        float s = max(dot(normalize(vDir), sunDir), 0.0);
        col += vec3(1.0, 0.95, 0.82) * (pow(s, 350.0) * 1.2 + pow(s, 18.0) * 0.16);
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  const sky = new THREE.Mesh(skyGeo, skyMat);
  sky.renderOrder = -10;
  scene.add(sky);

  // ---- 光照 ----
  scene.add(new THREE.HemisphereLight(0xeaf6ff, 0xb9cbb4, 1.05));
  const sun = new THREE.DirectionalLight(0xfff4e0, 2.3);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xdfeaff, 0.55);
  fill.position.set(-400, 300, 500);
  scene.add(fill);

  // ---- 雾 ----
  scene.fog = new THREE.Fog(0xd9edfc, 3000, 12000);

  // ---- 大地盘（接住机场以外的一切远处）----
  const disc = new THREE.Mesh(
    new THREE.CircleGeometry(15000, 48),
    new THREE.MeshLambertMaterial({ color: 0x94bb81 }));
  disc.rotation.x = -Math.PI / 2;
  disc.position.y = -0.5;
  disc.receiveShadow = true;
  scene.add(disc);

  // ---- 云海（成团泡状贴图，沿航线走廊分布）----
  const cloudTex = [1, 2, 3].map(i => {
    const t = new THREE.TextureLoader().load(`assets/tex/cloud${i}.png`);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  });
  const cloudMat = cloudTex.map(t => new THREE.SpriteMaterial({
    map: t, transparent: true, opacity: 0.9, depthWrite: false, fog: true, toneMapped: false,
  }));
  const cloudGroup = new THREE.Group();
  const rand = mulberry32(2026);
  const put = (n, y0, y1, w0, w1, op) => {
    for (let i = 0; i < n; i++) {
      const m = cloudMat[i % 3].clone();
      m.opacity = op * (0.8 + rand() * 0.25);
      const s = new THREE.Sprite(m);
      const x = (rand() - 0.5) * 3800;
      const z = -1500 + rand() * 8200;          // 覆盖滑行→巡航全航线
      s.position.set(x, y0 + rand() * (y1 - y0), z);
      const w = w0 + rand() * (w1 - w0);
      s.scale.set(w, w * (0.45 + rand() * 0.18), 1);
      s.renderOrder = 3;
      cloudGroup.add(s);
    }
  };
  put(175, 268, 396, 330, 660, 1.0);   // 低云毯（穿云层+云海，密不透地）
  put(46, 830, 960, 360, 660, 0.45);   // 高云稀薄
  scene.add(cloudGroup);

  // ---- 云海大平面（飞机高于云层时渐显：从上看连续云海，从下看是云底）----
  const sea = document.createElement('canvas'); sea.width = sea.height = 512;
  const sg = sea.getContext('2d');
  sg.fillStyle = '#f0f7fe'; sg.fillRect(0, 0, 512, 512);           // 云隙淡蓝
  const srng = mulberry32(77);
  for (let i = 0; i < 560; i++) {
    const big = srng() < 0.18;
    const x = srng() * 512, y = srng() * 512, r = big ? 90 + srng() * 70 : 14 + srng() * 52;
    const grd = sg.createRadialGradient(x, y, 0, x, y, r);
    const wh = 251 + Math.floor(srng() * 5);
    grd.addColorStop(0, `rgba(${wh},${wh},255,${(0.7 + srng() * 0.3).toFixed(2)})`);
    grd.addColorStop(1, `rgba(${wh},${wh},255,0)`);
    sg.fillStyle = grd;
    sg.beginPath(); sg.arc(x, y, r, 0, 7); sg.fill();
  }
  const seaTex = new THREE.CanvasTexture(sea);
  seaTex.wrapS = seaTex.wrapT = THREE.RepeatWrapping;
  seaTex.repeat.set(6, 6);
  seaTex.colorSpace = THREE.SRGBColorSpace;
  const seaMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(30000, 30000),
    new THREE.MeshBasicMaterial({ map: seaTex, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, fog: true }));
  seaMesh.material.toneMapped = false;   // 跳过 ACES 压灰，云海纯白
  seaMesh.rotation.x = -Math.PI / 2;
  seaMesh.position.y = 332;
  seaMesh.renderOrder = 2;
  scene.add(seaMesh);

  return {
    sky, sun, clouds: cloudGroup, seaMesh,
    update(t, cam, st) {
      sky.position.copy(cam.position);       // 天空永远以相机为中心
      cloudGroup.position.x = Math.sin(t * 0.008) * 30;
      // 云海随飞行高度渐显（穿出云层后铺在脚下）；纹理锚定世界坐标防滑动
      if (st) {
        const k = Math.max(0, Math.min(1, (st.alt - 285) / 105));
        seaMesh.material.opacity = k * 0.97;
        seaMesh.position.x = st.x; seaMesh.position.z = st.z;
        seaTex.offset.set(st.x / 5000, -st.z / 5000);
      }
    },
  };
}

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

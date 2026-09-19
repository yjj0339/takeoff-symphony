/* 凌云起飞 · 环境：天空穹顶 / 太阳 / 双层云海 / 雾 */
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

  // ---- 天空穹顶 shader（浅色渐变 + 太阳光晕）----
  const skyGeo = new THREE.SphereGeometry(5200, 32, 18);
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: {
      top: { value: new THREE.Color(0x6db9ec) },
      mid: { value: new THREE.Color(0xcfe8f7) },
      hor: { value: new THREE.Color(0xf2f9fd) },
      sunDir: { value: new THREE.Vector3(0.42, 0.5, -0.75).normalize() },
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
  scene.add(sky);

  // ---- 光照 ----
  scene.add(new THREE.HemisphereLight(0xeaf6ff, 0xb9cbb4, 1.05));
  const sun = new THREE.DirectionalLight(0xfff4e0, 2.3);
  sun.position.set(630, 750, -1125);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xdfeaff, 0.55);
  fill.position.set(-400, 300, 500);
  scene.add(fill);

  // ---- 雾（浅蓝白，远景融合）----
  scene.fog = new THREE.Fog(0xe4f2fa, 2600, 7000);

  // ---- 云海（两层 sprite 群）----
  const cloudTex = [1, 2, 3].map(i => {
    const t = new THREE.TextureLoader().load(`assets/tex/cloud${i}.png`);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  });
  const cloudMat = cloudTex.map(t => new THREE.SpriteMaterial({
    map: t, transparent: true, opacity: 0.92, depthWrite: false, fog: false,
  }));
  const cloudGroup = new THREE.Group();
  const CLOUD_Y = 330;                 // 低云层（穿云层）
  const rand = mulberry32(2026);
  const put = (n, y0, y1, spread, scale0, scale1, opBase) => {
    for (let i = 0; i < n; i++) {
      const m = cloudMat[i % 3].clone();
      m.opacity = opBase * (0.75 + rand() * 0.3);
      const s = new THREE.Sprite(m);
      const a = rand() * Math.PI * 2, r = 120 + rand() * spread;
      s.position.set(Math.cos(a) * r + (rand() - 0.5) * 400, y0 + rand() * (y1 - y0), Math.sin(a) * r + (rand() - 0.5) * 400);
      const w = scale0 + rand() * (scale1 - scale0);
      s.scale.set(w, w * (0.42 + rand() * 0.2), 1);
      cloudGroup.add(s);
    }
  };
  put(210, CLOUD_Y - 55, CLOUD_Y + 60, 2600, 190, 430, 0.95);   // 低云毯（大范围覆盖起飞走廊）
  put(90, 820, 960, 4200, 260, 560, 0.55);                      // 高云（稀薄）
  scene.add(cloudGroup);

  return {
    sky, sun, clouds: cloudGroup, CLOUD_Y,
    update(t) { /* 云缓慢漂移 */
      cloudGroup.position.x = Math.sin(t * 0.008) * 30;
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

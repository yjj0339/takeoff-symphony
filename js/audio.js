/* 凌云起飞 · WebAudio 引擎声合成（无音频文件）
   层次：buzzsaw 锯齿组(叶片通过频率) + 宽频风扇噪声 + 喷流噪声 + 地面隆隆 + 风噪
*/
export class EngineAudio {
  constructor() {
    this.ctx = null;
    this.ready = false;
    this.muted = false;
    this.vol = 0.8;
  }
  async start() {
    if (this.ready) { this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AC();
    const ctx = this.ctx;
    this.master = ctx.createGain();
    this.master.gain.value = this.vol;
    this.master.connect(ctx.destination);

    // 白噪声 buffer（2s 循环）
    const len = ctx.sampleRate * 2;
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) {
      const w = Math.random() * 2 - 1;
      last = (last + 0.02 * w) / 1.02;
      d[i] = w * 0.5 + last * 3.2;   // 白+棕混合
    }
    const mkNoise = () => { const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true; s.start(); return s; };

    // -- 锯齿 buzzsaw（N1 基频）--
    this.saws = [];
    for (const det of [0, 7, -5]) {
      const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = 60; o.detune.value = det * 12;
      const g = ctx.createGain(); g.gain.value = 0;
      const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 900;
      o.connect(f); f.connect(g); g.connect(this.master); o.start();
      this.saws.push({ o, g, f });
    }
    // -- 风扇宽噪（bandpass 随 N1 升频）--
    this.fanNoise = mkNoise();
    this.fanBP = ctx.createBiquadFilter(); this.fanBP.type = 'bandpass'; this.fanBP.frequency.value = 500; this.fanBP.Q.value = 0.8;
    this.fanG = ctx.createGain(); this.fanG.gain.value = 0;
    this.fanNoise.connect(this.fanBP); this.fanBP.connect(this.fanG); this.fanG.connect(this.master);
    // -- 喷流（highpass，推力感）--
    this.jetNoise = mkNoise();
    this.jetHP = ctx.createBiquadFilter(); this.jetHP.type = 'highpass'; this.jetHP.frequency.value = 1400;
    this.jetG = ctx.createGain(); this.jetG.gain.value = 0;
    this.jetNoise.connect(this.jetHP); this.jetHP.connect(this.jetG); this.jetG.connect(this.master);
    // -- 地面隆隆（lowpass）--
    this.rumb = mkNoise();
    this.rumbLP = ctx.createBiquadFilter(); this.rumbLP.type = 'lowpass'; this.rumbLP.frequency.value = 90;
    this.rumbG = ctx.createGain(); this.rumbG.gain.value = 0;
    this.rumb.connect(this.rumbLP); this.rumbLP.connect(this.rumbG); this.rumbG.connect(this.master);
    // -- 风噪（速度）--
    this.wind = mkNoise();
    this.windBP = ctx.createBiquadFilter(); this.windBP.type = 'bandpass'; this.windBP.frequency.value = 900; this.windBP.Q.value = 0.5;
    this.windG = ctx.createGain(); this.windG.gain.value = 0;
    this.wind.connect(this.windBP); this.windBP.connect(this.windG); this.windG.connect(this.master);

    this.ready = true;
  }
  update(st) {
    if (!this.ready || this.muted) return;
    const now = this.ctx.currentTime;
    const set = (p, v, s = 0.09) => p.setTargetAtTime(v, now, s);
    const n1 = st.n1;
    // 锯齿：N1 22%→42Hz, 100%→136Hz
    const buzz = 38 + n1 * 100;
    this.saws.forEach(({ o, g, f }) => {
      set(o.frequency, buzz);
      set(g.gain, n1 * 0.085);
      set(f.frequency, 500 + n1 * 2200);
    });
    set(this.fanBP.frequency, 380 + n1 * 1500);
    set(this.fanG.gain, 0.015 + n1 * 0.22);
    set(this.jetG.gain, Math.max(0, n1 - 0.45) * 0.30);
    set(this.jetHP.frequency, 900 + n1 * 1800);
    set(this.rumbG.gain, st.onGround ? Math.min(1, st.spd / 60) * 0.5 : 0);
    set(this.windG.gain, st.spd > 55 ? Math.min(1, (st.spd - 55) / 90) * 0.14 : 0);
  }
  setMuted(m) {
    this.muted = m;
    if (this.ready) this.master.gain.setTargetAtTime(m ? 0 : this.vol, this.ctx.currentTime, 0.05);
  }
}

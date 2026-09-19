/* 凌云起飞 · HUD 绑定 */
import { PHASES, DURATION } from './flight.js';

const $ = id => document.getElementById(id);

export function initHUD({ onSeek }) {
  const el = {
    phaseName: $('phaseName'), phaseSub: $('phaseSub'), camLabel: $('camLabel'),
    speed: $('dSpeed'), alt: $('dAlt'), n1: $('dN1'), gear: $('dGear'),
    progress: $('progress'), progressPhase: $('progressPhase'), toast: $('toast'),
    play: $('btnPlay'),
  };
  // 进度条阶段刻度
  el.progressPhase.innerHTML = PHASES.map(p =>
    `<span style="left:${(p.t / DURATION * 100).toFixed(1)}%">${p.name}</span>`).join('');

  let toastTimer = 0;
  return {
    setPhase(st) {
      if (el.phaseName.textContent !== st.phase.name) {
        el.phaseName.style.opacity = 0;
        setTimeout(() => {
          el.phaseName.textContent = st.phase.name;
          el.phaseSub.textContent = st.phase.sub;
          el.phaseName.style.opacity = 1;
        }, 260);
      }
    },
    setData(st) {
      el.speed.textContent = Math.round(st.spd * 3.6);
      el.alt.textContent = Math.round(st.alt);
      el.n1.textContent = Math.round(st.n1 * 100);
      el.gear.textContent = st.gearT > 0.97 ? '起落架放下' : st.gearT < 0.03 ? '起落架收起' : '起落架动作中';
    },
    setProgress(t) {
      const v = Math.round(t / DURATION * 1000);
      el.progress.value = v;
      el.progress.style.setProperty('--p', (t / DURATION * 100).toFixed(2) + '%');
    },
    setCam(label) { el.camLabel.textContent = label; },
    setPlaying(p) { el.play.textContent = p ? '⏸' : '▶'; el.play.classList.toggle('on', !p); },
    toast(msg) {
      el.toast.textContent = msg;
      el.toast.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => el.toast.classList.remove('show'), 1800);
    },
    onProgress(cb) { el.progress.addEventListener('input', e => cb(e.target.value / 1000 * DURATION)); },
  };
}

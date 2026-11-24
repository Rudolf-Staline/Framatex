/* FRAMATEX — Tissu bleu en 3D (Three.js). Maillage déformé à chaque image (plis, ondulations),
   matériau physique « sheen » (reflet velouté des textiles), relief de tissage procédural,
   réaction douce au pointeur. Ne calcule rien quand le tissu n'est pas visible. */
import * as THREE from './vendor/three.module.min.js';

function weaveTexture(size = 256) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const cell = 8;
  for (let y = 0; y < size; y += cell) {
    for (let x = 0; x < size; x += cell) {
      const over = ((x / cell) + (y / cell)) % 2 === 0;
      const grad = over ? g.createLinearGradient(x, y, x + cell, y) : g.createLinearGradient(x, y, x, y + cell);
      grad.addColorStop(0, '#5a5a5a'); grad.addColorStop(.5, '#e6e6e6'); grad.addColorStop(1, '#5a5a5a');
      g.fillStyle = grad; g.fillRect(x, y, cell, cell);
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(22, 14);
  return tex;
}

export function mountFabric(host, {interactive = true} = {}) {
  const canvas = document.createElement('canvas');
  canvas.className = 'fabric3d-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none';
  host.prepend(canvas);
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true, powerPreference: 'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, .1, 50);
  camera.position.set(0, 0, 9);
  scene.add(new THREE.AmbientLight(0x9fb8d6, .55));
  const key = new THREE.DirectionalLight(0xffffff, 3.4); key.position.set(-6, 6, 2.5); scene.add(key);
  const rim = new THREE.DirectionalLight(0x2daae1, 2.2); rim.position.set(5, -2, 3); scene.add(rim);

  const SX = 160, SY = 100;
  const geo = new THREE.PlaneGeometry(9, 5.6, SX, SY);
  const base = geo.attributes.position.array.slice();
  const weave = weaveTexture();
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0x003b70, roughness: .78, metalness: 0, sheen: 1, sheenRoughness: .45, sheenColor: new THREE.Color(0x8fd4f3),
    bumpMap: weave, bumpScale: .9, side: THREE.DoubleSide,
  });
  const cloth = new THREE.Mesh(geo, mat);
  cloth.rotation.set(-.62, .22, -.18);
  cloth.scale.set(1.25, 1.25, 1);
  scene.add(cloth);

  let visible = false, raf = 0, px = 0, py = 0, tx = 0, ty = 0, influence = 0, t0 = performance.now();
  function displace(time) {
    const p = geo.attributes.position.array;
    for (let i = 0; i < p.length; i += 3) {
      const x = base[i], y = base[i + 1];
      // Grands plis tombants + ondulation fine + froissé léger.
      let z = Math.sin(x * .9 + time * .45) * .55 * (1 - (y + 2.8) / 9)
        + Math.sin(x * 2.3 - y * .6 + time * .8) * .09
        + Math.abs(Math.sin(x * 1.6 + y * .35 + time * .3)) * -.32
        + Math.sin(y * 3.4 + x * .4 + time * 1.1) * .025;
      if (influence > .001) {
        const d = (x - px) * (x - px) + (y - py) * (y - py);
        z += Math.exp(-d * .9) * .45 * influence;
      }
      p[i + 2] = z;
    }
    geo.attributes.position.needsUpdate = true;
    geo.computeVertexNormals();
  }
  function resize() {
    const r = host.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / Math.max(1, r.height);
    camera.position.z = camera.aspect < 1 ? 12 : 9;
    camera.updateProjectionMatrix();
  }
  function frame(now) {
    raf = 0;
    if (!visible) return;
    px += (tx - px) * .08; py += (ty - py) * .08;
    influence += ((interactive && host.matches(':hover') ? 1 : 0) - influence) * .05;
    displace((now - t0) / 1000);
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }
  if (interactive) {
    host.addEventListener('pointermove', e => {
      const r = host.getBoundingClientRect();
      tx = ((e.clientX - r.left) / r.width - .5) * 9;
      ty = -((e.clientY - r.top) / r.height - .5) * 5.6;
    });
  }
  addEventListener('resize', resize);
  new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (visible && !raf) raf = requestAnimationFrame(frame);
  }).observe(host);
  resize();
  displace(0); renderer.render(scene, camera);
  host.classList.add('has-fabric3d');
  return {renderer, scene};
}

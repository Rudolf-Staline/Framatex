/* FRAMATEX — Le Dossier Jaune en 3D (Three.js, synchronisé avec le défilement).
   Objets modélisés : chemise à onglet extrudée, couverture articulée, feuilles, quatre
   sous-dossiers, écran présentant une capture anonymisée de la plateforme. Ombres portées,
   textures procédurales (papier, kraft). Chargé à la demande ; rendu seulement quand la
   scène est visible et qu'elle bouge. */
import * as THREE from './vendor/three.module.min.js';

const FOLDERS = [
  ['jaune', 0xd4a20a, 'Sous-dossier jaune'], ['rose', 0xc9568a, 'Sous-dossier rose'],
  ['bleu', 0x2a7cc7, 'Sous-dossier bleu'], ['vert', 0x3a8f5c, 'Sous-dossier vert'],
];
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = t => t * t * (3 - 2 * t);
const phase = (p, a, b) => ease(clamp((p - a) / (b - a)));
const mix = (a, b, t) => a + (b - a) * t;

function grainTexture(base, lines = false, size = 512) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = base; g.fillRect(0, 0, size, size);
  const img = g.getImageData(0, 0, size, size);
  for (let i = 0; i < img.data.length; i += 4) {
    const n = (Math.random() - .5) * 18;
    img.data[i] += n; img.data[i + 1] += n; img.data[i + 2] += n * .8;
  }
  g.putImageData(img, 0, 0);
  if (lines) {
    g.fillStyle = 'rgba(0,59,112,.85)'; g.fillRect(48, 52, 220, 14);
    g.fillStyle = 'rgba(58,70,86,.32)';
    for (let y = 100; y < size - 40; y += 26) g.fillRect(48, y, (size - 96) * (.55 + Math.random() * .45), 7);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

// Chemise à onglet : profil extrudé (épaisseur réelle, bords biseautés).
function folderShape(w, h, tab = true) {
  const s = new THREE.Shape();
  s.moveTo(0, 0); s.lineTo(w, 0); s.lineTo(w, h);
  if (tab) { s.lineTo(w * .46, h); s.lineTo(w * .40, h + .22); s.lineTo(w * .08, h + .22); s.lineTo(w * .03, h); }
  s.lineTo(0, h); s.lineTo(0, 0);
  return s;
}
function slab(shape, depth, material) {
  const geo = new THREE.ExtrudeGeometry(shape, {depth, bevelEnabled: true, bevelThickness: .006, bevelSize: .006, bevelSegments: 2});
  geo.rotateX(-Math.PI / 2);            // à plat, face visible vers le haut
  const mesh = new THREE.Mesh(geo, material);
  mesh.castShadow = true; mesh.receiveShadow = true;
  return mesh;
}

export function mountFolderScene(section) {
  const canvas = section.querySelector('canvas');
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true, powerPreference: 'high-performance'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, .1, 60);
  scene.add(new THREE.HemisphereLight(0xeaf4ff, 0x0a2545, 1.1));
  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(-3.5, 7, 4.5); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  Object.assign(key.shadow.camera, {left: -5, right: 5, top: 5, bottom: -5, near: 1, far: 20});
  key.shadow.bias = -.0005; key.shadow.radius = 4;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x8fd4f3, .9); rim.position.set(4, 3, -4); scene.add(rim);

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.ShadowMaterial({opacity: .22}));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -.02; ground.receiveShadow = true; scene.add(ground);

  // --- Dossier jaune physique -------------------------------------------------------
  const W = 3.1, H = 2.2;
  const kraft = new THREE.MeshStandardMaterial({color: 0xf2c230, map: grainTexture('#f3cf55'), roughness: .82, metalness: 0});
  const kraftInner = new THREE.MeshStandardMaterial({color: 0xf6d77a, map: grainTexture('#f7dc87'), roughness: .9});
  const folder = new THREE.Group();
  const back = slab(folderShape(W, H, true), .03, kraftInner);
  back.position.set(-W / 2, 0, H / 2);
  folder.add(back);
  const hinge = new THREE.Group();               // charnière le long du dos (bord gauche)
  hinge.position.set(-W / 2, .035, 0);
  const front = slab(folderShape(W, H * .94, false), .03, kraft);
  front.position.set(0, 0, H / 2);
  hinge.add(front);
  folder.add(hinge);
  scene.add(folder);

  // --- Feuilles ---------------------------------------------------------------------
  const paperTex = grainTexture('#fbfbf8', true);
  const sheets = [];
  for (let i = 0; i < 5; i++) {
    const sheet = new THREE.Mesh(new THREE.BoxGeometry(2.5, .008, 1.85),
      new THREE.MeshStandardMaterial({color: 0xffffff, map: paperTex, roughness: .95}));
    sheet.castShadow = true; sheet.receiveShadow = true;
    sheet.position.set(0, .05 + i * .012, .05);
    scene.add(sheet); sheets.push(sheet);
  }

  // --- Quatre sous-dossiers ------------------------------------------------------------
  const subs = FOLDERS.map(([slug, color], i) => {
    const mat = new THREE.MeshStandardMaterial({color, roughness: .62, map: grainTexture('#ffffff', false, 256), emissive: color, emissiveIntensity: .12});
    const g = new THREE.Group();
    const body = slab(folderShape(1.05, .76, true), .025, mat);
    body.position.set(-.525, 0, .38);
    g.add(body);
    scene.add(g);
    return g;
  });

  // --- Écran : capture anonymisée de la plateforme -----------------------------------
  const screen = new THREE.Group();
  const bezel = new THREE.Mesh(new THREE.BoxGeometry(3.4, 2.18, .08), new THREE.MeshStandardMaterial({color: 0x0b1d33, roughness: .35, metalness: .4}));
  bezel.castShadow = true;
  const capture = new THREE.TextureLoader().load(section.dataset.capture, () => kick());
  capture.colorSpace = THREE.SRGBColorSpace; capture.anisotropy = 8;
  const display = new THREE.Mesh(new THREE.PlaneGeometry(3.24, 2.025), new THREE.MeshBasicMaterial({map: capture, transparent: true, opacity: 0, toneMapped: false}));
  display.position.z = .043;
  screen.add(bezel, display);
  scene.add(screen);

  // --- Animation pilotée par le défilement (valeur amortie) ---------------------------
  let target = 0, current = 0, raf = 0, visible = false, pointerX = 0;
  const steps = [...section.querySelectorAll('[data-fd-step]')];

  function layout(p) {
    const enter = phase(p, 0, .1), open = phase(p, .08, .28), fan = phase(p, .24, .46), split = phase(p, .42, .64), platform = phase(p, .6, .86);
    // Le dossier glisse sur la table, s'ouvre comme un livre (charnière gauche) et se recentre.
    folder.position.set(mix(1.2, 0, enter) + open * W / 2, 0, mix(1.8, 0, enter) + platform * .4);
    folder.rotation.y = mix(-.55, 0, enter) + pointerX * .05;
    folder.scale.setScalar(mix(1, .72, platform));
    hinge.rotation.z = open * Math.PI * .985;
    // Les feuilles s'élèvent et s'ouvrent en éventail, tournées vers le lecteur.
    sheets.forEach((sheet, i) => {
      const k = i - 2;
      sheet.position.set(open * W / 2 * mix(1, .72, platform) + mix(0, k * .62, fan), mix(.05 + i * .012, 1.05 + Math.abs(k) * -.12 + i * .03, fan) - platform * .9, mix(.05, -.2 - Math.abs(k) * .12, fan));
      sheet.rotation.set(mix(0, .95, fan), mix(0, k * -.12, fan), mix(0, k * -.08, fan));
      sheet.scale.setScalar(mix(1, .74, fan));
      sheet.visible = enter > .02 && platform < .96;
    });
    // Les quatre sous-dossiers sortent du dossier et se rangent devant, côte à côte.
    subs.forEach((g, i) => {
      const local = clamp(split * 1.7 - i * .22);
      g.position.set(mix(W / 2, (i - 1.5) * 1.22, ease(local)), .03 + .05 * Math.sin(local * Math.PI), mix(.2, 1.85, ease(local)) - platform * .9);
      g.rotation.set(-.08 * local, mix(.4, 0, local), 0);
      g.scale.setScalar(mix(.4, 1, ease(local)) * mix(1, .7, platform));
      g.visible = local > .01;
    });
    // La plateforme : un écran s'élève derrière le dossier et présente l'application.
    screen.visible = platform > .01;
    screen.position.set(0, mix(-.4, 1.25, platform), -1.6);
    screen.rotation.x = mix(-.35, -.06, platform);
    screen.scale.setScalar(mix(.6, 1, platform));
    display.material.opacity = platform;
    // La scène occupe la droite : le texte reste lisible dans la colonne de gauche.
    const shift = camera.aspect > 1.25 ? -1.45 : -.8;
    camera.position.set(shift + pointerX * .3, mix(8.2, 5.2, platform), mix(8.6, 9.2, platform));
    camera.lookAt(shift, mix(.25, 1.05, platform), mix(.2, -1, platform));
    const step = p < .08 ? 0 : p < .24 ? 1 : p < .42 ? 2 : p < .6 ? 3 : 4;   // étapes alignées sur les phases
    steps.forEach((el, i) => el.classList.toggle('is-current', i === Math.min(steps.length - 1, step)));
  }

  function resize() {
    const r = canvas.parentElement.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / Math.max(1, r.height);
    camera.fov = camera.aspect < 1.2 ? 44 : 34;
    camera.updateProjectionMatrix();
  }
  function progress() {
    const r = section.getBoundingClientRect();
    return clamp(-r.top / Math.max(1, r.height - innerHeight));
  }
  function frame() {
    raf = 0;
    current += (target - current) * .3;            // inertie faible : réponse rapide au défilement
    layout(current);
    renderer.render(scene, camera);
    if (visible && Math.abs(target - current) > .001) raf = requestAnimationFrame(frame);
  }
  const kick = () => { target = progress(); if (!raf && visible) raf = requestAnimationFrame(frame); };
  addEventListener('scroll', kick, {passive: true});
  addEventListener('resize', () => { resize(); kick(); });
  section.addEventListener('pointermove', e => { pointerX = (e.clientX / innerWidth - .5) * 2; current -= .0006; kick(); });
  new IntersectionObserver(entries => { visible = entries[0].isIntersecting; if (visible) kick(); }).observe(section);
  resize(); target = current = progress(); layout(current); renderer.render(scene, camera);
  section.classList.add('is-3d');
  return {renderer, scene, progress: () => current};
}

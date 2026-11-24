/* Chargement différé de la scène 3D du Dossier Jaune.
   Alternative statique (capture de la plateforme et étapes lisibles) si : écran étroit,
   prefers-reduced-motion, WebGL indisponible ou échec de chargement. */
(function () {
  'use strict';
  var section = document.querySelector('[data-folder3d]');
  if (!section) return;
  function fallback() { section.classList.add('is-static'); section.classList.remove('is-3d'); }
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var gl = false;
  try { var c = document.createElement('canvas'); gl = !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); } catch (e) { gl = false; }
  if (reduce || !gl || window.innerWidth < 820 || !('IntersectionObserver' in window)) { fallback(); return; }
  section.classList.add('is-pending-3d');
  var io = new IntersectionObserver(function (entries) {
    if (!entries[0].isIntersecting) return;
    io.disconnect();
    import('/assets/landing/folder3d.js?v=cinematic-3d-1')
      .then(function (m) { section.classList.remove('is-pending-3d'); window.__framatexFolder3d = m.mountFolderScene(section); })
      .catch(function () { fallback(); });
  }, {rootMargin: '800px 0px'});
  io.observe(section);
})();

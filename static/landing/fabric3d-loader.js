/* Chargement différé du tissu 3D pour tout élément [data-fabric3d].
   Rien n'est chargé sur écran étroit, sous prefers-reduced-motion ou sans WebGL :
   le fond bleu statique reste en place. Exposé pour les pages de connexion. */
(function () {
  'use strict';
  function supported() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || window.innerWidth < 820 || !('IntersectionObserver' in window)) return false;
    try { var c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch (e) { return false; }
  }
  function attach(host, options) {
    if (!host || host.dataset.fabricReady || !supported()) return;
    host.dataset.fabricReady = '1';
    var io = new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      import('/assets/landing/fabric3d.js?v=cinematic-3d-1').then(function (m) { m.mountFabric(host, options || {}); }).catch(function () {});
    }, {rootMargin: '400px 0px'});
    io.observe(host);
  }
  window.framatexFabric = attach;
  document.querySelectorAll('[data-fabric3d]').forEach(function (host) { attach(host); });
})();

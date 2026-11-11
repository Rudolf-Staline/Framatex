// FRAMATEX — Landing publique : en-tête, menu mobile, assets manquants, apparition au scroll.
(function () {
  'use strict';

  // En-tête : fine bordure une fois la page défilée.
  var header = document.querySelector('[data-header]');
  if (header) {
    var onScroll = function () { header.classList.toggle('is-scrolled', window.scrollY > 8); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // Menu mobile.
  var toggle = document.querySelector('[data-nav-toggle]');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    var setOpen = function (open) {
      toggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    };
    toggle.addEventListener('click', function () { setOpen(toggle.getAttribute('aria-expanded') !== 'true'); });
    nav.addEventListener('click', function (evt) { if (evt.target.closest('a')) setOpen(false); });
    document.addEventListener('keydown', function (evt) {
      if (evt.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { setOpen(false); toggle.focus(); }
    });
  }

  // Asset absent (logo, photo) : afficher un repère technique explicite, jamais un visuel de remplacement.
  document.querySelectorAll('img[data-fallback]').forEach(function (img) {
    var holder = img.closest('[data-media]');
    if (!holder) return;
    var markMissing = function () { holder.classList.add('is-missing'); };
    img.addEventListener('error', markMissing);
    if (img.loading !== 'lazy' && img.complete && img.naturalWidth === 0) markMissing();
  });

  // Apparition légère des blocs situés sous la ligne de flottaison uniquement.
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion || !('IntersectionObserver' in window)) return;
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-revealed');
      entry.target.classList.remove('is-pending');
      observer.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  var fold = window.innerHeight;
  document.querySelectorAll('.reveal').forEach(function (el) {
    if (el.getBoundingClientRect().top < fold) return;
    el.classList.add('is-pending');
    observer.observe(el);
  });
})();

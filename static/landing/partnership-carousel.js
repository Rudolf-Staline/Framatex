/* Carrousel du partenariat FRAMATEX × École Centrale Casablanca.
   Défilement toutes les 5 s (désactivé si l'utilisateur réduit les animations), pause au survol,
   au focus et par bouton ; flèches, indicateurs, clavier, glissement tactile, agrandissement. */
(function () {
  'use strict';
  var root = document.querySelector('[data-carousel]');
  if (!root) return;
  var slides = Array.prototype.slice.call(root.querySelectorAll('.pcar-slide'));
  var dots = Array.prototype.slice.call(root.querySelectorAll('[data-pcar-dot]'));
  var status = root.querySelector('[data-pcar-status]');
  var pauseBtn = root.querySelector('[data-pcar-pause]');
  var dialog = root.querySelector('.pcar-lightbox');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var index = 0, timer = null, hovering = false, userPaused = reduce.matches, startX = null, swiped = false, visible = false;

  function show(next, announce) {
    index = (next + slides.length) % slides.length;
    slides.forEach(function (slide, i) {
      var active = i === index;
      slide.classList.toggle('is-active', active);
      slide.classList.toggle('is-before', i === (index - 1 + slides.length) % slides.length);
      slide.setAttribute('aria-hidden', active ? 'false' : 'true');
      slide.querySelector('.pcar-zoom').tabIndex = active ? 0 : -1;
    });
    dots.forEach(function (dot, i) { if (i === index) dot.setAttribute('aria-current', 'true'); else dot.removeAttribute('aria-current'); });
    if (announce && status) status.textContent = 'Photographie ' + (index + 1) + ' sur ' + slides.length;
  }
  function running() { return visible && !userPaused && !hovering && !document.hidden && !(dialog && dialog.open); }
  function schedule() {
    clearTimeout(timer);
    if (running()) timer = setTimeout(function () { show(index + 1, false); schedule(); }, 5000);
  }
  function syncPause() {
    pauseBtn.setAttribute('aria-pressed', String(userPaused));
    pauseBtn.setAttribute('aria-label', userPaused ? 'Reprendre le défilement' : 'Mettre en pause le défilement');
    root.classList.toggle('is-paused', userPaused);
  }

  root.querySelector('[data-pcar-prev]').addEventListener('click', function () { show(index - 1, true); schedule(); });
  root.querySelector('[data-pcar-next]').addEventListener('click', function () { show(index + 1, true); schedule(); });
  dots.forEach(function (dot, i) { dot.addEventListener('click', function () { show(i, true); schedule(); }); });
  pauseBtn.addEventListener('click', function () { userPaused = !userPaused; syncPause(); schedule(); });
  root.addEventListener('mouseenter', function () { hovering = true; schedule(); });
  root.addEventListener('mouseleave', function () { hovering = false; schedule(); });
  root.addEventListener('focusin', function () { hovering = true; schedule(); });
  root.addEventListener('focusout', function (e) { if (!root.contains(e.relatedTarget)) { hovering = false; schedule(); } });
  root.addEventListener('keydown', function (e) {
    if (dialog && dialog.open) return;
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(index - 1, true); schedule(); }
    if (e.key === 'ArrowRight') { e.preventDefault(); show(index + 1, true); schedule(); }
  });
  var stage = root.querySelector('.pcar-stage');
  // Les images ne déclenchent pas de glisser-déposer natif (qui annulerait le geste).
  stage.querySelectorAll('img').forEach(function (img) { img.draggable = false; });
  stage.addEventListener('dragstart', function (e) { e.preventDefault(); });
  stage.addEventListener('pointerdown', function (e) { startX = e.clientX; swiped = false; });
  stage.addEventListener('pointercancel', function () { startX = null; });
  stage.addEventListener('pointerup', function (e) {
    if (startX === null) return;
    var dx = e.clientX - startX; startX = null;
    swiped = Math.abs(dx) > 40;
    if (swiped) { show(index + (dx < 0 ? 1 : -1), true); schedule(); }
  });
  document.addEventListener('visibilitychange', schedule);

  // Agrandissement : boîte de dialogue native, navigation au clavier, fermeture par Échap.
  function openAt(i) {
    if (!dialog || typeof dialog.showModal !== 'function') return;
    show(i, false);
    var img = slides[index].querySelector('img');
    var big = dialog.querySelector('img');
    big.src = img.currentSrc || img.src; big.alt = img.alt;
    if (!dialog.open) dialog.showModal();
    schedule();
  }
  root.querySelectorAll('[data-pcar-open]').forEach(function (button) {
    button.addEventListener('click', function () { if (swiped) { swiped = false; return; } openAt(Number(button.dataset.pcarOpen)); });
  });
  if (dialog) {
    dialog.querySelector('[data-pcar-close]').addEventListener('click', function () { dialog.close(); });
    dialog.querySelectorAll('[data-pcar-lb]').forEach(function (b) { b.addEventListener('click', function () { openAt(index + Number(b.dataset.pcarLb)); }); });
    dialog.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') openAt(index - 1);
      if (e.key === 'ArrowRight') openAt(index + 1);
    });
    dialog.addEventListener('click', function (e) { if (e.target === dialog) dialog.close(); });
    dialog.addEventListener('close', function () { slides[index].querySelector('.pcar-zoom').focus(); schedule(); });
  }
  reduce.addEventListener && reduce.addEventListener('change', function () { if (reduce.matches) { userPaused = true; syncPause(); } schedule(); });
  // Défilement seulement quand le carrousel est visible : aucun travail hors écran.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) { visible = entries[0].isIntersecting; schedule(); }, {threshold: 0.25}).observe(root);
  } else { visible = true; }
  root.classList.add('is-ready');
  show(0, false); syncPause(); schedule();
})();

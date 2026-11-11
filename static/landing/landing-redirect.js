// Compatibilité des liens existants : les étiquettes papier / QR codes pointent
// vers « /#/launch/<id> ». Depuis que « / » sert la page d'accueil publique,
// ces liens sont renvoyés vers l'espace FRAMATEX qui sait les ouvrir.
(function () {
  'use strict';
  var hash = window.location.hash || '';
  if (/^#\/launch\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(hash)) {
    window.location.replace('/espace-framatex' + hash);
  }
})();

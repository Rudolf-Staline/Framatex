'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const read = file => fs.readFileSync(file, 'utf8');
const source = read('static/app.js');
const page = read('static/index.html');
const css = read('static/design-026.css');
const legacy = read('static/design-019.css');
assert(source.includes('login-page login-rebalanced'), 'Original login layout must remain mounted');
assert(source.includes('function renderSpaceChoice()'), 'Historical entry-space selector must exist');
assert(source.includes('Choisissez votre espace'), 'Historical selection heading missing');
assert(source.includes('data-space="internal"'), 'Internal space action missing');
assert(source.includes('href="/partners?space=client"'), 'Client must use partner portal');
assert(source.includes('href="/partners?space=supplier"'), 'Supplier must use partner portal');
assert(source.includes("app.querySelector('#change-space').addEventListener('click',renderSpaceChoice)"), 'Return to selection must work');
assert(source.includes('catch{renderSpaceChoice()}})();'), 'Visitor must land on selector, not login');
assert(read('static/partners.js').includes("chosenPartnerSpace === 'supplier'"), 'Partner destination must recognize supplier context');
for (const part of ['login-stage','login-visual-orbit','login-folder-back','login-folder-middle','login-folder-front','login-form-brand','login-title']) {
  assert(source.includes(part), 'Historic login part missing: '+part);
}
for (const element of ['id="login-form"','id="login-error"','id="email"','id="password"']) {
  assert(source.includes(element), 'Auth form element missing: '+element);
}
assert(source.includes("await api('/api/auth/login'"), 'Login endpoint must stay unchanged');
assert(source.includes("await navigate('home')"), 'Post-login routing must stay unchanged');
assert(page.includes('/assets/design-026.css'), 'Load historical login stylesheet');
assert(page.indexOf('/assets/design-026.css') > page.indexOf('/assets/design-019.css'), 'Load after blue theme');
assert(css.includes('/* Framatex 0.26 — Login équilibré'), 'Authentic original 0.26 design expected');
assert(css.includes('linear-gradient(156deg,#f6ce62 0%,#eaba42 66%,#e0ad2d 100%)'), 'Original yellow folder illustration missing');
assert(css.includes('@media(max-width:620px)'), 'Original mobile behavior missing');
assert(!legacy.includes('/* Framatex · Retour au jaune'), 'Do not keep improvised CSS override');
console.log('Historic Framatex 0.26 login layout, mobile and auth bindings: OK');

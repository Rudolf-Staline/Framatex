'use strict';
const fs=require('fs'),assert=require('node:assert/strict');
const access=fs.readFileSync('static/access-admin.js','utf8');
const app=fs.readFileSync('static/app.js','utf8');
const dossier=fs.readFileSync('static/dossier.js','utf8');
const css=fs.readFileSync('static/brand/access.css','utf8');
const dossierCss=fs.readFileSync('static/brand/dossier.css','utf8');

// La matrice est individuelle : aucun préréglage global de « nouvelles cases ».
assert(!access.includes('Droits des nouvelles cases'));
for(const level of ['Aucun accès','Lecture seule','Dépôt sans validation','Responsable','Personnalisé…']) assert(access.includes(level),level);
assert(access.includes('data-acc-level'));
assert(access.includes('data-acc-detail'));
assert(access.includes('Copier les affectations d’une autre commande'));
assert(access.includes('Retirer des accès ?'));
assert(access.includes("const actionsFor = key"));
// Les détails de commande emploient les capacités de la commande courante,
// pas une union de droits d'autres commandes.
for(const capability of ['folder.access_label','f.can_download','f.can_write']) assert(app.includes(capability),capability);
assert(dossier.includes("folder.access_label || 'Lecture seule'"));
assert(dossier.includes("folder.access_label || 'Accès restreint'"));
// L'ouverture d'une commande ne dépend plus de tous les modules secondaires et
// ne force plus le jaune pour un technicien limité au bleu.
assert(app.includes('optionalLaunchRequest'));
assert(app.includes('detail.folders.find(item=>item.can_read)'));
assert(app.includes("state.me=await api('/api/auth/me')"));
assert(!dossier.includes("djOriginalOpenLaunch(id, folder || 'jaune'"));
assert(dossier.includes('module(s) secondaire(s) sont indisponibles'));
assert(dossierCss.includes('.dj-access-level'));
for(const selector of ['.acc-level','.acc-matrix-guide','.acc-copy-option']) assert(css.includes(selector),selector);
assert(css.includes('@media (max-width: 760px)'));
console.log('UX accès : matrice individuelle, niveaux, confirmation et adaptation technicien OK');

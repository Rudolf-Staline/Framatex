'use strict';
const fs=require('fs'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/business-memory.js','utf8');

// Le bouton et le formulaire reposent sur les droits effectifs retournés par
// le serveur, jamais sur document.write dans le dossier Jaune.
assert(source.includes('/api/workspace/business-memory/options'));
assert(!source.includes("can('document.write','jaune')?'<button class=\"primary\" id=\"bm-add\""));
for(const id of ['bm-launch','bm-folder','folder_slug','bm-add-folder-note']) assert(source.includes(id),id);
for(const label of ['Sous-dossier jaune','Sous-dossier rose','Sous-dossier bleu','Sous-dossier vert']) assert(source.includes(label),label);
assert(source.includes('f.slug===folder.value&&f.can_read'));
assert(source.includes('launch_id:overlay.querySelector'));
assert(source.includes('folder_slug:overlay.querySelector'));
console.log('Mémoire métier : formulaire et bouton pilotés par la commande/sous-dossier autorisés OK');

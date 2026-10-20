'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const js=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-022.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.indexOf('design-022.css')>html.indexOf('design-021.css'));
assert(css.includes('background:#fff') && css.includes('sidebar-light'));
assert(css.includes('position:sticky') && css.includes('@media(max-width:760px)'));
assert(css.includes('data-folder-theme'));
const ctx={window:{addEventListener:()=>{}},document:{querySelector:()=>({})},console,setTimeout,clearTimeout};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
const output=vm.runInContext(`(()=>{
 state.me={name:'Administratrice Démo',roles:['Administrateur'],admin:true};
 state.view='dossier';
 const normal=sidebar();
 state.view='detail';state.folder='rose';
 const inside=sidebar();
 state.view='admin';
 const admin=sidebar();
 state.me={name:'Opérateur',roles:['Employé'],admin:false};
 state.view='dossier';
 const limited=sidebar();
 return {normal,inside,admin,limited};
})()`,ctx);
assert(output.normal.includes('sidebar-rail'));
assert(output.normal.includes('aria-label="Navigation principale"'));
for(const view of ['dossier','controls','rex']){
 assert(output.normal.includes('data-view="'+view+'"'));
}
assert(output.normal.includes('data-view="dossier" title="Dossier Jaune" aria-current="page"'));
assert(!output.normal.includes('data-view="assistant"'));
assert(js.includes("else if(view==='assistant')openFloatingAssistant()"));
assert(output.inside.includes('data-view="launches"')); // Un dossier par commande : accès rétabli.
assert(!output.normal.includes('data-view="notifications"'));
assert(!output.normal.includes('data-view="audit"'));
assert(!output.normal.includes('data-view="actions"'));
assert(output.normal.includes('data-view="pilot"'));
assert(output.admin.includes('class="rail-management" open'));
assert(!output.normal.includes('data-view="audit"'));
assert(!output.limited.includes('data-view="audit"'));
assert(!output.limited.includes('data-view="admin"'));
assert(output.normal.includes('id="logout"'));
assert(!output.normal.includes('sidebar-assistant'));
console.log('Sidebar blanche: navigation, permissions, actif et responsive valides');

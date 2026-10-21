'use strict';
// Historical sheets are bundled into the compatibility layer.
const legacy=require('node:fs').readFileSync('static/legacy-ui.css','utf8');
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const app=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-027.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
const loginCss=fs.readFileSync('static/design-026.css','utf8');
const folderCss=fs.readFileSync('static/design-024.css','utf8');
assert(legacy.includes('/* design-027.css */'));
assert(legacy.indexOf('/* design-027.css */')>legacy.indexOf('/* design-026.css */'));
assert(css.includes('.app-shell .page-heading'));
assert(css.includes('.app-shell .toolbar .searchbar'));
assert(css.includes('.app-shell .panel tbody tr.item-row:focus-visible'));
assert(css.includes('.app-shell .admin-advanced'));
assert(css.includes('.app-shell[data-folder-theme] .simple-detail-head'));
assert(css.includes('.app-shell[data-folder-theme] .folder-tabs'));
assert(css.includes('.floating-assistant-panel'));
assert(css.includes('@media(max-width:480px)'));
assert(css.includes('prefers-reduced-motion'));
assert(css.includes('#dfb239'), 'Warm dossier accent absent');
assert(!css.includes('background:linear-gradient(165deg,#5188ed'), 'Blue sidebar reintroduced');
assert(!css.includes('.login-page'), 'Login page styling must remain intact');
assert(loginCss.includes('login-rebalanced'), 'Approved login layout missing');
assert(folderCss.includes('data-folder-theme="rose"'));
assert(folderCss.includes('data-folder-theme="bleu"'));
assert(folderCss.includes('data-folder-theme="vert"'));
assert(app.includes('class="admin-advanced"'));
assert(app.includes('class="admin-advanced-content"'));
assert(app.includes('Paramètres avancés'));
assert(!app.includes('Journal d’activité<span class="brand-accent">'));
assert(html.includes('/assets/order-identification.js'));
assert(app.includes('data-launch="${e(l.id)}" tabindex="0"'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length,'Malformed CSS braces');
// Minimal rendering check for the redesigned launch listing with live mocked results.
const root={innerHTML:'',querySelector:()=>({addEventListener(){},onclick:null}),querySelectorAll:()=>[]};
const ctx={console,setTimeout,clearTimeout,document:{querySelector:()=>root,addEventListener(){}},window:{addEventListener(){}},syncFloatingAssistant:()=>{}};
vm.createContext(ctx);
vm.runInContext(app.slice(0,app.lastIndexOf('(async function init(){')),ctx);
vm.runInContext(fs.readFileSync('static/order-identification.js','utf8'),ctx);
vm.runInContext([
 'state.me={name:"Admin",admin:true,permissions:[],roles:["Administrateur"]};',
 'api=async path=>path==="/api/launches"?[{id:"L1",name:"Lancement fictif",status:"À compléter",client_name:"Client fictif",created_at:"2026-10-18T10:00:00Z"}]:[];',
 'syncFloatingAssistant=()=>{};',
 'bindLaunchRows=()=>{};'
].join('\n'),ctx);
const table=vm.runInContext("orderTable([{id:'L1',name:'Dossier fictif',order_ref:'CMD-1',client_name:'Client fictif',status:'À compléter',identification:{workshop:'Atelier A'}}])",ctx);
assert(table.includes('CMD-1'));
assert(table.includes('Client fictif'));
assert(table.includes('Atelier A'));
assert(table.includes('data-order-open="L1"'));
assert(table.includes('<button type="button"'));
console.log('Framatex: themed folders, responsive styles and order listing OK');

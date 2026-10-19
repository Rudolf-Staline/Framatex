'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('static/index.html','utf8');
const css=fs.readFileSync('static/design-032.css','utf8');
const js=fs.readFileSync('static/app.js','utf8');
assert(html.includes('/assets/design-032.css'),'atelier stylesheet not loaded');
assert(html.indexOf('design-032.css')>html.indexOf('design-031.css'));
assert(html.includes('Space+Grotesk')&&html.includes('IBM+Plex+Sans'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);
for(const selector of ['.atelier-home-cover','.atelier-ledger','.dash-folder-link','.atelier-dossier-cover','.sidebar-rail.sidebar-light','.login-rebalanced h1']){
 assert(css.includes(selector),'visual system missing '+selector);
}
assert(css.includes('@media(max-width:760px)'),'mobile required');
assert(css.includes('prefers-reduced-motion'),'motion opt-out required');
for(const label of ['Framatex','Dossiers jaunes','Accueil','Dossiers']){
 assert(js.includes(label),'business label missing: '+label);
}
const elements=new Map();
function node(selector){
 if(!elements.has(selector))elements.set(selector,{value:'',innerHTML:'',textContent:'',dataset:{},
  addEventListener(){},focus(){},setAttribute(){}});
 return elements.get(selector);
}
const app={querySelector:node,querySelectorAll:()=>[]};
const ctx={window:{addEventListener(){}},document:{querySelector:s=>s==='#app'?app:node(s)},console,setTimeout,clearTimeout};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
const sidebar=vm.runInContext(`(()=>{
 state.view='home';state.me={admin:true,name:'Agent test',roles:['Administrateur'],permissions:[]};
 return sidebar();
})()`,ctx);
assert(sidebar.includes('atelier-logo-letter'));
assert(sidebar.includes('atelier-brand-sub'));
assert(sidebar.includes('data-view="actions"'));
assert(sidebar.includes('Comprendre Framatex'));
ctx.fakeItems=[{id:'1',name:'Pantalon prototype',client_name:'Client Test',status:'À compléter',created_at:'2026-10-19T10:00:00Z'}];
vm.runInContext(`(
 ()=>{
 mount=(s)=>{globalThis.viewHtml=s};
 api=async path=>{
  if(path==='/api/workspace/priorities')return {items:[],total:0};
  if(path==='/api/dashboard')return {launches:1,documents:3};
  if(path==='/api/launches')return fakeItems;
  throw new Error('Bad API path '+path);
 };
 bindLaunchRows=()=>{};bindPriorityWidget=()=>{};
})()`,ctx);
(async()=>{
 await vm.runInContext('home()',ctx);
 const view=ctx.viewHtml;
 assert(view.includes('atelier-home-cover'));
 assert(view.includes('atelier-ledger'));
 assert(view.includes('atelier-paper-card'));
 for(const slug of ['jaune','rose','bleu','vert'])assert(view.includes('dash-folder-'+slug));
 assert(view.includes('atelier-folder-symbol')===false,'folder number should reuse existing semantic symbol class');
 assert(view.includes('>01</span>')&&view.includes('>04</span>'));
 assert(view.includes('Pantalon prototype'));
 assert(view.includes('data-quick-folder="vert"'));
 assert(!view.includes('FM-2024-001'),'no invented production data');
 assert(js.includes('id="ux-tool-description">${e(chosen[3])}'),'tool explanation must interpolate');
 console.log('Framatex Atelier 0.32: navigation, folder tabs, dashboard, typography and responsive CSS OK');
})().catch(err=>{console.error(err);process.exitCode=1});

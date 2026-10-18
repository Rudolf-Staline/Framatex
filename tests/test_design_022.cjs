'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const js=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-022.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('/assets/design-022.css'));
assert(css.includes('sidebar-light') && css.includes('background:#fff'));
assert(css.includes('@media(max-width:760px)'));
for(const folder of ['jaune','rose','bleu','vert'])assert(css.includes('.dash-folder-'+folder));
assert(!js.includes('class="command-hero"'));
assert(!js.includes('class="home-rail"'));

const listeners={},elements=new Map();
function control(key){
 if(!elements.has(key))elements.set(key,{value:'',innerHTML:'',textContent:'',dataset:{},
  addEventListener(name,handler){listeners[key+':'+name]=handler},focus(){}});
 return elements.get(key);
}
const app={querySelector:control,querySelectorAll(selector){
 if(selector==='[data-quick-folder]')return ['jaune','rose','bleu','vert'].map(slug=>control('folder:'+slug));
 return [];
}};
for(const slug of ['jaune','rose','bleu','vert'])control('folder:'+slug).dataset.quickFolder=slug;
const ctx={console,setTimeout,clearTimeout,
 document:{querySelector(selector){return selector==='#app'?app:control(selector)}},
 window:{addEventListener(){}}};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
const fakeLaunches=[
 {id:'l1',name:'Veste technique',client_name:'Client A',orli_ref:null,order_ref:'C-123',status:'À compléter',created_at:'2026-10-13T12:00:00Z',updated_at:'2026-10-15T12:00:00Z'},
 {id:'l2',name:'Pantalon cargo',client_name:'Client B',orli_ref:'ORLI-4',order_ref:'C-987',status:'En cours',created_at:'2026-10-12T12:00:00Z',updated_at:'2026-10-16T12:00:00Z'}
];
ctx.fakeLaunches=fakeLaunches;
vm.runInContext([
 'globalThis.renderedDashboard="";globalThis.openedFolders=[];',
 'state.me={name:"Admin démo",admin:true,permissions:[],roles:["Administrateur"]};',
 'mount=html=>{globalThis.renderedDashboard=html};',
 'api=async path=>{',
 ' if(path==="/api/workspace/priorities")return {total:2,items:[]};',
 ' if(path==="/api/dashboard")return {launches:2,documents:7};',
 ' if(path==="/api/launches")return fakeLaunches;',
 ' throw new Error("Unexpected API "+path);',
 '};',
 'bindPriorityWidget=()=>{};bindLaunchRows=()=>{};openNewLaunch=()=>{};',
 'openLaunch=async(id,folder)=>{openedFolders.push([id,folder])};'
].join('\n'),ctx);
(async()=>{
 await vm.runInContext('home()',ctx);
 const out=ctx.renderedDashboard;
 assert(out.includes('simple-home dashboard-022'));
 assert(out.includes('Mes lancements')&&out.includes('À suivre'));
 assert(out.includes('<strong>2</strong>')&&out.includes('<strong>7</strong>'));
 assert(out.includes('data-home-tab="incomplete"'));
 assert(out.includes('Veste technique')&&out.includes('Pantalon cargo'));
 assert(out.includes('data-quick-folder="jaune"')&&out.includes('data-quick-folder="vert"'));
 assert(out.includes('id="quick-launch"')&&out.includes('ORLI-4'));
 assert(!out.includes('248')&&!out.includes('FM-2024-001'));
 assert(!out.includes('Activité récente'));
 listeners['folder:rose:click']();
 await Promise.resolve();
 assert.equal(ctx.openedFolders[0][0],'l1');
 assert.equal(ctx.openedFolders[0][1],'rose');
 control('#home-search').value='pantalon';
 listeners['#home-search:input']();
 assert(control('#home-launch-table').innerHTML.includes('Pantalon cargo'));
 assert(!control('#home-launch-table').innerHTML.includes('Veste technique'));
 assert(js.includes('data-folder-theme'));
 console.log('Framatex 0.22: dashboard, filtres et raccourcis OK');
})().catch(err=>{console.error(err);process.exitCode=1});

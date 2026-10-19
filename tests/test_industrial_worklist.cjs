'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('static/index.html','utf8');
const foundation=fs.readFileSync('static/ui-foundation.css','utf8');
const interfaceCss=fs.readFileSync('static/design-030.css','utf8');
const appSource=fs.readFileSync('static/app.js','utf8');
const approvals=fs.readFileSync('static/approvals.js','utf8');
assert(html.includes('family=IBM+Plex+Sans'));
const sheets=[...html.matchAll(/<link rel="stylesheet" href="([^"]+)"/g)].map(x=>x[1]);
assert.deepEqual(sheets,['/assets/ui-foundation.css','/assets/design-030.css']);
assert(!foundation.includes('@import'),'No stale font imports inside merged CSS');
assert.equal((foundation.match(/\{/g)||[]).length,(foundation.match(/\}/g)||[]).length);
assert.equal((interfaceCss.match(/\{/g)||[]).length,(interfaceCss.match(/\}/g)||[]).length);
assert(interfaceCss.includes('.iw-folder-status'));
assert(interfaceCss.includes('.dash-table tbody td'));
assert(interfaceCss.includes('@media(max-width:760px)'));
assert(!appSource.includes('simple-stats dash-stats'),'No ornamental KPI cards');
assert(!appSource.includes('lc-folder-access'),'Folder shortcuts belong inside the dossier');
assert(!approvals.includes('Que signifie cette validation ?'),'No verbose explainer panel');

const listeners={},nodes=new Map();
function node(name){
 if(!nodes.has(name))nodes.set(name,{value:'',textContent:'',innerHTML:'',dataset:{},
  addEventListener(type,callback){listeners[name+':'+type]=callback},focus(){},setAttribute(){}});
 return nodes.get(name);
}
const app={querySelector:node,querySelectorAll:()=>[]};
const ctx={console,setTimeout,clearTimeout,document:{querySelector:sel=>sel==='#app'?app:node(sel)},window:{addEventListener(){}}};
vm.createContext(ctx);
vm.runInContext(appSource.slice(0,appSource.lastIndexOf('(async function init(){')),ctx);
ctx.testLaunches=[
 {id:'d1',name:'Lancement technique A',status:'En cours',order_ref:'C-01',client_name:'Client A',orli_ref:null,updated_at:'2026-10-19'},
 {id:'d2',name:'Commande pièces B',status:'À compléter',order_ref:'C-02',client_name:'Client B',orli_ref:'ORLI-7',updated_at:'2026-10-19'},
 {id:'d3',name:'Archivage terminé',status:'Clôturé',order_ref:'C-03',client_name:'Client C',orli_ref:null,updated_at:'2026-10-19'}
];
vm.runInContext([
 'state.me={admin:true,name:"Agent de fabrication"};',
 'mount=html=>{globalThis.pageHtml=html};',
 'bindPriorityWidget=()=>{};bindLaunchRows=()=>{};',
 'api=async path=>{',
 ' if(path==="/api/workspace/priorities")return {total:1,items:[{id:"a",priority:"high",title:"Pièce à vérifier",launch_name:"Lancement technique A",launch_id:"d1",area:"documents"}]};',
 ' if(path==="/api/launches")return testLaunches;',
 ' throw new Error(path);};'
].join('\n'),ctx);
(async()=>{
 await vm.runInContext('home()',ctx);
 const page=ctx.pageHtml;
 assert(page.includes('Suivi des lancements'));
 assert(page.includes('1 en cours · 1 à compléter'));
 assert(page.includes('Points signalés'));
 assert(page.includes('Pièce à vérifier'));
 assert(page.includes('ORLI-7'));
 assert(!page.includes('Bonjour '));
 assert(!page.includes('Documents accessibles'));
 assert(!page.includes('data-quick-folder'));
 node('#home-search').value='pièces B';
 listeners['#home-search:input']();
 assert(node('#home-launch-table').innerHTML.includes('Commande pièces B'));
 assert(!node('#home-launch-table').innerHTML.includes('Lancement technique A'));
 console.log('Industrial workspace: real worklist, search, factual metrics, 2 CSS files OK');
})().catch(err=>{console.error(err);process.exitCode=1});

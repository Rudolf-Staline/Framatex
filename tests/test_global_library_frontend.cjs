'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
const source=fs.readFileSync('static/global-library.js','utf8');
const html=fs.readFileSync('static/index.html','utf8');
const originalApp=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-031.css','utf8');
assert(html.includes('/assets/global-library.js'));
assert(html.includes('/assets/design-031.css'));
assert(html.indexOf('/assets/global-library.js')>html.indexOf('/assets/app.js'));
assert(originalApp.includes("if(view==='dossier'||view==='home')await globalLibraryPage()"));
assert(originalApp.includes("await navigate('dossier')"));
assert(!source.includes("api('/api/launches'"));
assert(!source.includes('Nouveau dossier'));
assert(css.includes('.global-folders') && css.includes('@media(max-width:760px)'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);

let page='',lastApi='',count={textContent:''},table={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null};
const app={
 querySelector(key){
  if(key==='#global-doc-results')return table;
  if(key==='#global-result-count')return count;
  return {querySelectorAll:()=>[],addEventListener(){},dataset:{},onclick:null};
 },
 querySelectorAll:()=>[]
};
const sample={
 unique:true,name:'Dossier Jaune',
 folders:[
  {slug:'jaune',label:'Technique',can_read:true,can_write:true,count:1,documents:[{
    id:'d1',title:'Fiche d’emploi',doc_type:'Fiche technique',folder:'jaune',
    orli_ref:'ORLI-42',created_at:'2026-10-19T12:00:00Z',
    latest:{number:1,original_name:'fiche.pdf',created_at:'2026-10-19T12:00:00Z'},
    versions:[{number:1,original_name:'fiche.pdf',created_at:'2026-10-19T12:00:00Z'}]
  }]},
  {slug:'rose',label:'Réception',can_read:true,can_write:false,count:0,documents:[]},
  {slug:'bleu',label:'Douane',can_read:false,can_write:false,count:0,documents:[]},
  {slug:'vert',label:'Facturation',can_read:true,can_write:false,count:0,documents:[]},
 ]
};
const ctx={app,state:{view:'home'},console,
 api:async path=>{lastApi=path;return path.endsWith('/controls')?{rules:[],expectations:[],comparisons:[]}:sample},
 mount:body=>{page=body},
 e:x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;'),
 icon:()=>'□',niceDate:v=>v||'—',can:()=>true,
 showErr:err=>{throw err}
};
vm.createContext(ctx);
vm.runInContext(source,ctx);
(async()=>{
 await vm.runInContext('globalLibraryPage()',ctx);
 assert.equal(lastApi,'/api/dossier-jaune/controls');
 assert.equal(ctx.state.view,'dossier');
 assert(page.includes('Espace documentaire')&&page.includes('Les quatre sous-dossiers'));
 assert(page.includes('data-global-folder="jaune"'));
 assert(page.includes('data-global-folder="rose"'));
 assert(page.includes('data-global-folder="bleu"'));
 assert(page.includes('data-global-folder="vert"'));
 assert(table.innerHTML.includes('Fiche d’emploi'));
 assert(table.innerHTML.includes('ORLI-42'));
 assert(!page.includes('Nouveau dossier'));
 vm.runInContext("globalQuery='introuvable';globalRenderRows()",ctx);
 assert(table.innerHTML.includes('Aucun résultat'));
 vm.runInContext("globalFolder='bleu';globalQuery='';renderGlobalLibrary()",ctx);
 assert(table.innerHTML.includes('Accès à cette rubrique réservé'));
 console.log('Dossier Jaune V2: shared folders, version rows, search and restrictions OK');
})().catch(err=>{console.error(err);process.exitCode=1});

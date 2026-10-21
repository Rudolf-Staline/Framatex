'use strict';
// Historical sheets are bundled into the compatibility layer.
const legacy=require('node:fs').readFileSync('static/legacy-ui.css','utf8');
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const html=fs.readFileSync('static/index.html','utf8');
const css=fs.readFileSync('static/design-034.css','utf8');
const js=fs.readFileSync('static/global-library.js','utf8');

assert(fs.readFileSync('static/atelier.css','utf8').includes('Arial'));

assert(legacy.indexOf('/* design-034.css */')>legacy.indexOf('/* design-033.css */'));
assert(css.includes('--lc-font:"DM Sans"') && css.includes('--ui-display:"Plus Jakarta Sans"'));
assert(css.includes('.global-card-overline'));
assert(css.includes('.global-card-footer'));
assert(css.includes('.app-shell .global-workspace .global-folder-card'));
assert(css.includes('.global-file-icon.global-format-pdf'));
assert(css.includes('prefers-reduced-motion'));
assert(css.includes('max-width:760px'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);

const htmlPane={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null};
const countPane={textContent:''};
const dummy={querySelectorAll:()=>[],addEventListener(){},focus(){},value:'all'};
const app={
 querySelector(key){
   if(key==='#global-doc-results')return htmlPane;
   if(key==='#global-result-count')return countPane;
   return dummy;
 },
 querySelectorAll:()=>[]
};
const source={
 name:'Dossier Jaune',unique:true,
 folders:[
 {slug:'jaune',label:'Technique',can_read:true,can_write:true,count:2,documents:[
  {id:'p',title:'Cahier des charges',doc_type:'Notice',folder:'jaune',orli_ref:'ORLI-001',created_at:'2026-10-19T12:00:00Z',latest:{number:2,original_name:'cahier.pdf',created_at:'2026-10-19T12:00:00Z'},versions:[{number:1,original_name:'cahier.pdf',created_at:'2026-10-19T11:00:00Z'},{number:2,original_name:'cahier.pdf',created_at:'2026-10-19T12:00:00Z'}]},
  {id:'x',title:'Tableau',doc_type:'Fiche de suivi',folder:'jaune',orli_ref:null,created_at:'2026-10-19T12:00:00Z',latest:{number:1,original_name:'suivi.xlsx',created_at:'2026-10-19T12:00:00Z'},versions:[{number:1,original_name:'suivi.xlsx',created_at:'2026-10-19T12:00:00Z'}]}
 ]},
 {slug:'rose',label:'Réception',can_read:true,can_write:true,count:0,documents:[]},
 {slug:'bleu',label:'Douane',can_read:false,can_write:false,count:0,documents:[]},
 {slug:'vert',label:'Facturation',can_read:true,can_write:false,count:0,documents:[]}
 ]
};
let rendered='';
const ctx={
 app,state:{view:'dossier',dossierFolder:'jaune',sidebarDossierOpen:true},
 console,document:{activeElement:null},
 api:async()=>source,
 mount:html=>{rendered=html},
 e:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;'),
 icon:()=>'<svg></svg>',
 niceDate:()=> '19 oct. 2026',
 can:()=>true,
 showErr:err=>{throw err}
};
vm.createContext(ctx);
vm.runInContext(js,ctx);
ctx.sample=source;
vm.runInContext('globalIndex=sample;globalFolder="jaune";renderGlobalLibrary()',ctx);
assert(!rendered.includes('role="tablist"'));
assert(rendered.includes('saffron-document-toolbar'));
assert(rendered.includes('aria-label="Documents du sous-dossier Jaune"'));

assert(htmlPane.innerHTML.includes('global-format-pdf'));
assert(htmlPane.innerHTML.includes('global-format-excel'));
assert(htmlPane.innerHTML.includes('global-select-all'));
assert(!rendered.includes('saffron-context'));
assert(rendered.includes('register-upload'));

vm.runInContext('globalType="pdf";globalRenderRows()',ctx);
assert(htmlPane.innerHTML.includes('cahier.pdf'));
assert(!htmlPane.innerHTML.includes('suivi.xlsx'));
assert.equal(countPane.textContent,'1 document');
vm.runInContext('globalType="excel";globalRenderRows()',ctx);
assert(htmlPane.innerHTML.includes('suivi.xlsx'));
assert(!htmlPane.innerHTML.includes('cahier.pdf'));
vm.runInContext('globalType="all";globalQuery="ORLI-001";globalRenderRows()',ctx);
assert(htmlPane.innerHTML.includes('cahier.pdf'));
assert(!htmlPane.innerHTML.includes('suivi.xlsx'));
vm.runInContext('globalQuery="";globalFolder="bleu";renderGlobalLibrary()',ctx);
assert(rendered.includes('disabled'));
assert(htmlPane.innerHTML.includes('Accès à cette rubrique réservé.'));
console.log('Document library: fonts, compact tabs, file filters, permissions and responsive styles OK');

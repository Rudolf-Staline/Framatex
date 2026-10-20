'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('static/global-library.js','utf8');
const escaped=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let page='',modalBody='',download=null,writable=true,actionNodes={},prefill=null;
const contextPane={innerHTML:'',querySelectorAll:()=>[]};
const table={innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[]};
const handlers={};
const dummy={value:'',focus(){},addEventListener(){}};
const count={textContent:''};
const app={
 querySelector(selector){
  if(selector==='#global-context-issues')return contextPane;
  if(selector==='#global-doc-results')return table;
  if(selector==='#global-result-count')return count;
  if(selector==='#global-record-issue')return {addEventListener:(_,fn)=>{handlers.record=fn}};
  return dummy;
 },querySelectorAll:()=>[]
};
const folders=['jaune','rose','bleu','vert'].map(slug=>({slug,label:slug,can_read:true,can_write:true,documents:[]}));
const doc=(id,title,ref,date,name='fiche.pdf')=>({id,title,folder:'jaune',orli_ref:ref,doc_type:'Fiche',created_at:date,latest:{number:2,original_name:name,created_at:date},versions:[{number:1,original_name:name,created_at:date},{number:2,original_name:name,created_at:date}]});
folders[0].documents=[doc('one','Zèbre <script>',' ORLI-1 ','2026-10-20T12:00:00Z'),doc('two','Alpha','ORLI-2','2026-10-19T12:00:00Z','fiche.xlsx')];
const archive={folders};
const pair=[{value:'1500',unit:'pièce'},{value:'1450',unit:'pièce'}];
const report={rules:[{id:'r'}],comparisons:[
 {name:'Quantité',status:'difference',orli_ref:'orli-1',folders:['jaune','rose'],pair},
 {name:'Autre référence',status:'difference',orli_ref:'ORLI-2',folders:['jaune','rose'],pair},
 {name:'Conforme',status:'consistent',orli_ref:'ORLI-1',folders:['jaune','rose'],pair},
],expectations:[
 {title:'Bon de réception',document_type:'BR',status:'missing',folder:'rose',orli_ref:'ORLI-1'},
 {title:'Autre lancement',document_type:'BR',status:'missing',folder:'jaune',orli_ref:'ORLI-2'},
 {title:'Présent',status:'present',folder:'jaune',orli_ref:'ORLI-1'},
]};
const ctx={console,app,archive,report,
 state:{view:'dossier',me:{admin:true}},document:{activeElement:null},
 controlState:{},api:async path=>path.endsWith('/controls')?report:archive,
 mount:body=>{page=body},e:escaped,icon:()=>'<svg></svg>',niceDate:x=>x,
 can:()=>writable,showErr:e=>{throw e},
 modal:(_title,body)=>{modalBody=body},
 overlay:{querySelector:selector=>actionNodes[selector]||(actionNodes[selector]={onclick:null,addEventListener(_event,fn){this.click=fn}}),querySelectorAll:()=>[]},
 openRexEditor:async(_record,values)=>{prefill=values},knowledgeDialogFocus(){},
};
vm.createContext(ctx);vm.runInContext(source,ctx);
const run=code=>vm.runInContext(code,ctx);
(async()=>{
 await run('globalLibraryPage()');
 assert.equal(run('globalSelectedId'),'one');
 assert(table.innerHTML.includes('&lt;script&gt;'));
 assert(!table.innerHTML.includes('<script>'));
 assert.equal(run('globalContextIssues().length'),2);
 assert(contextPane.innerHTML.includes('1\u202f500 / 1\u202f450 pièce'));
 assert(contextPane.innerHTML.includes('Bon de réception manquant'));
 assert(!contextPane.innerHTML.includes('Autre lancement'));
 assert(!contextPane.innerHTML.includes('Conforme'));
 handlers.record();await Promise.resolve();
 assert.deepEqual(JSON.parse(JSON.stringify(prefill)),{folder:'jaune',orli_ref:' ORLI-1 ',document_id:'one'});
 run("globalSelectedId='two';renderGlobalContext()");
 assert.equal(run('globalContextIssues().length'),2);
 assert(contextPane.innerHTML.includes('Autre lancement'));
 assert(!contextPane.innerHTML.includes('Bon de réception'));
 run("globalQuery='ORLI-2';globalRenderRows()");
 assert.equal(run('globalSelectedId'),'two');
 assert.equal(count.textContent,'1 document');
 assert(!table.innerHTML.includes('Zèbre'));
 run("globalQuery='';globalType='excel';globalRenderRows()");
 assert(table.innerHTML.includes('Alpha'));
 assert(!table.innerHTML.includes('Zèbre'));
 run("globalType='all';globalSort='name';globalRenderRows()");
 assert(table.innerHTML.indexOf('Alpha')<table.innerHTML.indexOf('Zèbre'));
 assert.equal(run('globalIndex.folders[0].documents[0].id'),'one','sorting must not mutate the archive');
 run("globalSelectedId='one';globalControlReport.comparisons[0].status='unit_mismatch';globalControlReport.comparisons[0].pair[1].unit='kg';renderGlobalContext()");
 assert(contextPane.innerHTML.includes('Unités différentes'));
 assert(contextPane.innerHTML.includes('1\u202f500 / 1\u202f450 · unités différentes'));
 run("globalDocumentActions('one')");
 assert(modalBody.includes('v2 · fiche.pdf')&&modalBody.includes('v1 · fiche.pdf'));
 assert(modalBody.indexOf('v2 ·')<modalBody.indexOf('v1 ·'));
 assert(modalBody.includes('Modifier la référence ORLI'));
 ctx.capture=(id,v)=>{download=[id,v]};run('globalDownload=capture');
 actionNodes['#global-action-download'].onclick();
 assert.deepEqual(download,['one',2]);
 writable=false;run("globalDocumentActions('one')");
 assert(!modalBody.includes('Modifier la référence ORLI'));
 folders[0].can_write=false;run('renderGlobalLibrary()');
 assert(!page.includes('id="global-upload"'));
 assert(!page.includes('id="global-record-issue"'));
 folders[0].can_read=false;run('globalRenderRows()');
 assert(table.innerHTML.includes('Accès à cette rubrique réservé'));
 assert.equal(run('globalContextIssues().length'),0);
 folders[0].can_read=true;writable=true;
 ctx.api=async path=>{if(path.endsWith('/controls'))throw new Error('temporary');return archive};
 await run('globalLibraryPage()');
 assert(contextPane.innerHTML.includes('momentanément indisponibles'));
 assert(!contextPane.innerHTML.includes('Aucun point'));
 let release;
 ctx.api=path=>path.endsWith('/controls')?Promise.resolve(report):new Promise(resolve=>{release=resolve});
 const pending=run('globalLibraryPage()');
 const previous=page;ctx.state.view='rex';release(archive);await pending;
 assert.equal(page,previous,'a late library response must not replace another page');
 console.log('Safran: scoped real findings, units, errors, filters, version actions, REX prefill and late responses OK');
})().catch(error=>{console.error(error);process.exitCode=1});

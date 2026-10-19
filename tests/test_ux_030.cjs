'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const appSrc=fs.readFileSync('static/app.js','utf8');
const workSrc=fs.readFileSync('static/workspace.js','utf8');
const approvalsSrc=fs.readFileSync('static/approvals.js','utf8');
const css=fs.readFileSync('static/design-030.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('/assets/design-030.css'));
assert(html.indexOf('design-030.css')>html.indexOf('design-029.css'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);
assert(css.includes('.ux-task-tabs') && css.includes('.ux-role-grid'));
for(const src of [appSrc,workSrc,approvalsSrc])new vm.Script(src);

const app={querySelector:()=>null,querySelectorAll:()=>[]};
const overlay={querySelector:()=>({onclick:null,addEventListener(){}}),querySelectorAll:()=>[]};
const ctx={console,setTimeout,clearTimeout,window:{addEventListener(){}},
  document:{querySelector:s=>s==='#app'?app:overlay}};
vm.createContext(ctx);
vm.runInContext(appSrc.slice(0,appSrc.lastIndexOf('(async function init(){')),ctx);
vm.runInContext(workSrc,ctx);
vm.runInContext(approvalsSrc,ctx);
const result=vm.runInContext(`(()=>{
  state.me={admin:true,name:'Administrateur',roles:['Administrateur']};
  let help,role;
  modal=(title,body)=>{if(title==='Comprendre Framatex')help=body;else if(title==='Créer un rôle utilisateur')role=body};
  const sidebarHtml=sidebar();
  showUsageHelp();
  openNewRole();
  return {sidebarHtml,help,role};
})()`,ctx);
assert(result.sidebarHtml.includes('data-view="actions" title="À traiter"'));
assert(!result.sidebarHtml.includes('data-view="notifications" title="Notifications" aria-current="page"'));
assert(result.sidebarHtml.includes('Comprendre Framatex'));
assert(result.help.includes('Profil documentaire'));
assert(result.help.includes('Circuit de validation'));
assert(result.role.includes('Déposer'));
assert(result.role.includes('Autorisations avancées'));
assert(result.role.includes('document.read:jaune'));
assert(result.role.includes('document.write:vert'));
const sample=[
  {id:'missing:1',launch_id:'1',launch_name:'Dossier A',title:'Facture manquante',
   description:'Vert',priority:'high',area:'documents',folder:'vert',can_act:true,
   next_step:'Déposer la facture',deadline:null},
  {id:'missing:2',launch_id:'2',launch_name:'Dossier B',title:'Pièce non accessible',
   description:'Rose',priority:'high',area:'documents',folder:'rose',can_act:false,deadline:null}
];
ctx.testItems=sample;
const summary=vm.runInContext("prioritySummary({items:testItems})",ctx);
assert(summary.includes('Facture manquante'));
assert(!summary.includes('Pièce non accessible'), 'Non-actionable items belong in the follow-up tab');
const card=vm.runInContext('priorityCard(testItems[0])',ctx);
assert(card.includes('data-workspace-folder="vert"'));
assert(card.includes('Je peux agir'));
assert(card.includes('Déposer la facture'));
const item={template:{name:'Contrôle technique'},document_id:'doc1',document_title:'Fiche technique',
  folder:'jaune',version:2,can_start:true,previous:[],run:null};
ctx.approvalReport={items:[item]};
const approvalHtml=vm.runInContext('(()=>{state.approvalOverview=approvalReport;return renderApprovals()})()',ctx);
assert(approvalHtml.includes('Demander une validation'));
assert(approvalHtml.includes('une version précise'));
console.log('Framatex UX 0.30: navigation claire, aide, rôles, tâches et validations OK');

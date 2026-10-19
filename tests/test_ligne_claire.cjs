'use strict';
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const appjs=fs.readFileSync('static/app.js','utf8');
const approvals=fs.readFileSync('static/approvals.js','utf8');
const css=fs.readFileSync('static/design-030.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('family=Inter'), 'approved typeface missing');
assert(html.includes('/assets/design-030.css'), 'stylesheet missing');
assert(html.indexOf('design-030.css')>html.indexOf('design-029.css'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);
for(const rule of ['lc-global-search','lc-folder-access','lc-documents-layout','lc-detail-summary','lc-approval-layout']){
 assert(css.includes(rule),rule+' style missing');
}
const nodes=new Map();
function element(name){
 if(!nodes.has(name))nodes.set(name,{value:'',innerHTML:'',textContent:'',dataset:{},
   addEventListener(){},setAttribute(){},focus(){},scrollIntoView(){}});
 return nodes.get(name);
}
const root={querySelector:element,querySelectorAll:()=>[]};
const ctx={console,window:{addEventListener(){}},document:{querySelector:n=>n==='#app'?root:element(n)},setTimeout,clearTimeout};
vm.createContext(ctx);
vm.runInContext(appjs.slice(0,appjs.lastIndexOf('(async function init(){')),ctx);
vm.runInContext(approvals,ctx);
vm.runInContext([
 'globalThis.lastHtml="";',
 'mount=html=>{lastHtml=html};',
 'state.me={name:"Agent Test",admin:true,permissions:[],roles:["Administrateur"]};',
 'state.folder="jaune";',
 'bindPriorityWidget=()=>{};',
 'bindLaunchRows=()=>{};',
 'api=async path=>{',
 '  if(path==="/api/workspace/priorities")return {total:2,items:[]};',
 '  if(path==="/api/dashboard")return {launches:2,documents:11};',
 '  if(path==="/api/launches")return [{id:"1",name:"Lot chemises",status:"En cours",client_name:"A"},{id:"2",name:"Lot polos",status:"À compléter",client_name:"B"}];',
 '  throw new Error(path);',
 '};'
].join('\n'),ctx);
(async()=>{
 await vm.runInContext('home()',ctx);
 assert(ctx.lastHtml.includes('Vos dossiers récents'));
 assert(ctx.lastHtml.includes('Accès rapides aux sous-dossiers'));
 assert(ctx.lastHtml.includes('Dossiers actifs'));
 assert(ctx.lastHtml.includes('Documents accessibles'));
 assert(ctx.lastHtml.includes('Dossiers à compléter'));
 assert(ctx.lastHtml.includes('<strong>11</strong>'), 'metrics must come from server');
 assert(ctx.lastHtml.includes('data-quick-folder="rose"'));
 assert(ctx.lastHtml.includes('data-quick-folder="vert"'));
 assert(!ctx.lastHtml.includes('24 Dossiers actifs'),'must not use image-only numbers');
 vm.runInContext([
  'for(const method of ["renderCompleteness","renderWorkflow","renderQuality","renderIntake","renderPaper","renderSpec","renderMail","renderImpactSimulation","renderOrliReconciliation","renderMaterialReport","renderApprovals","renderSharing"])globalThis[method]=()=>"";',
  'for(const method of ["bindCompleteness","bindWorkflow","bindQuality","bindIntake","bindPaper","bindSpec","bindMail","bindImpactSimulation","bindOrliReconciliation","bindMaterialReport","bindApprovals","bindSharing"])globalThis[method]=()=>{};',
  'state.view="detail";',
  'state.detail={id:"L",name:"Lot chemises",status:"En cours",can_update:true,folders:["jaune","rose","bleu","vert"].map(slug=>({slug,label:slug,can_read:true,can_write:true,documents:slug==="jaune"?[{id:"d1",title:"Fiche emploi",doc_type:"Fiche d’emploi",latest:{number:2,original_name:"fiche.pdf",size:6000}}]:[]}))};',
  'state.approvalOverview={items:[{document_id:"d1",document_title:"Fiche emploi",folder:"jaune",version:2,previous:[],run:{status:"approved"}}]};',
  'renderDetail();'
 ].join('\n'),ctx);
 assert(ctx.lastHtml.includes('lc-documents-layout'));
 assert(ctx.lastHtml.includes('lc-detail-summary'));
 assert(ctx.lastHtml.includes('Fiche emploi'));
 assert(ctx.lastHtml.includes('Approuvée'));
 assert(ctx.lastHtml.includes('id="lc-open-validations"'));
 assert(ctx.lastHtml.includes('data-folder="rose"'));
 assert(!ctx.lastHtml.includes('class="command-hero"'));
 // Check the real approval renderer independently (not the detail stubs).
 const approvalHtml=vm.runInContext('renderApprovals()',ctx);
 assert(approvalHtml.includes('Faire valider un document'));
 assert(approvalHtml.includes('Que signifie cette validation ?'));
 console.log('Ligne claire: all three screens, real metrics, accessible folders and approval layout OK');
})().catch(err=>{console.error(err);process.exitCode=1});

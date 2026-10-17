// Tests sans dépendances npm : XSS échappées et présence des modules 0.3.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let a=fs.readFileSync('static/app.js','utf8');a=a.slice(0,a.lastIndexOf('(async function init(){'));
let b=fs.readFileSync('static/workflow.js','utf8');
const ctx={document:{querySelector:()=>({})},window:{addEventListener:()=>{}},console,setTimeout,clearTimeout};
vm.createContext(ctx);vm.runInContext(a,ctx);vm.runInContext(b,ctx);
const html=vm.runInContext(`(()=>{state.me={admin:true,permissions:[]};state.detail={id:'launch',folders:[]};
state.workflowReviews=[{document_id:'d1',document_title:'<script>alert(1)</script>',folder:'jaune',version:1,status:'to_review',last_comment:'',can_review:false,history:[]}];
state.workflowValues=[{key:'consommation_matiere',label:'Consommation matière',current:{value:'1.9',unit:'m/pièce',source_title:'Fiche test',source_version:1,source_is_current:true,revision:2,reason:''},history:[]}];
state.workflowImpacts=[{id:'a1',rule_name:'Une dépendance',instruction:'Vérifier les achats',source_folder:'jaune',target_folder:'rose',created_at:'2026-10-17T10:00:00',status:'to_review',old_value:'1.8 m',new_value:'1.9 m',can_review:true}];
return renderWorkflow()})()`,ctx);
for(const t of ['Décisions et impacts métier','Valeurs métier traçables','Propagation ciblée','Consommation matière','Une dépendance','1.9'])assert(html.includes(t),'Texte absent '+t);
assert(html.includes('&lt;script&gt;')&&!html.includes('<script>'));
console.log('Workflow 0.3 : rendu, valeurs, alertes et échappement OK.');

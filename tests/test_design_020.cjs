'use strict';
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const js=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-020.css','utf8');
const assistant=fs.readFileSync('static/assistant.js','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('design-020.css'));
assert(!js.includes('class="command-hero"') && !js.includes('class="home-rail"'));
assert(!js.includes('class="sidebar-assistant '));
assert(!assistant.includes('<aside class="assistant-context">'));
const ctx={console,window:{addEventListener:()=>{}},document:{querySelector:()=>({})},setTimeout,clearTimeout};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
const output=vm.runInContext(`(()=>{
 const rendered=[];
 app.querySelector=()=>({onclick:null,addEventListener:()=>{}});app.querySelectorAll=()=>[];
 mount=html=>rendered.push(html);
 for (const name of ['renderCompleteness','renderWorkflow','renderQuality','renderIntake','renderPaper','renderSpec','renderMail','renderImpactSimulation','renderOrliReconciliation','renderMaterialReport','renderApprovals','renderSharing']) globalThis[name]=()=>'<section class="preserved-module"></section>';
 for (const name of ['bindCompleteness','bindWorkflow','bindQuality','bindIntake','bindPaper','bindSpec','bindMail','bindImpactSimulation','bindOrliReconciliation','bindMaterialReport','bindApprovals','bindSharing']) globalThis[name]=()=>{};
 state.me={admin:true,name:'Admin',roles:['Administrateur'],permissions:[]};
 state.detail={id:'demo',name:'Lancement fictif',status:'En cours',created_at:'2026-10-18T00:00:00Z',updated_at:'2026-10-18T00:00:00Z',can_update:true,folders:[
 {slug:'jaune',label:'Technique',can_read:true,can_write:true,documents:[]},
 {slug:'rose',label:'Réception',can_read:true,can_write:true,documents:[]},
 {slug:'bleu',label:'Douane',can_read:true,can_write:true,documents:[]},
 {slug:'vert',label:'Facturation',can_read:true,can_write:true,documents:[]}
 ]};
 for(const folder of ['jaune','rose','bleu','vert']){state.folder=folder;renderDetail()}
 return rendered;
})()`,ctx);
assert.equal(output.length,4);
for(let i=0;i<4;i++){
 const folder=['jaune','rose','bleu','vert'][i];
 assert(output[i].includes('data-folder="'+folder+'" aria-pressed="true"'));
 assert.equal((output[i].match(/class="preserved-module"/g)||[]).length,12);
 assert(output[i].indexOf('simple-document-section')<output[i].indexOf('detail-view-tools'));
 assert(css.includes('data-folder-theme="'+folder+'"') || folder==='jaune'&&css.includes('data-folder-theme]{'));
}
assert(js.includes('data-folder-theme'));
assert(css.includes('var(--folder-bg)'));
console.log('Framatex 0.20: quatre thèmes contextuels, accueil épuré et modules préservés.');

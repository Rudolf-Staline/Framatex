'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const js=fs.readFileSync('static/app.js','utf8');
const workspace=fs.readFileSync('static/workspace.js','utf8');
const css=fs.readFileSync('static/design-028.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('design-028.css'));
assert(html.indexOf('design-028.css')>html.indexOf('design-027.css'));
assert(css.includes('.detail-tool-panel[hidden]'));
assert(css.includes('@media(max-width:760px)'));
assert(css.includes('detail-tool-stage'));
assert(css.includes('detail-tool-group'));
assert.equal((css.match(/\\{/g)||[]).length,(css.match(/\\}/g)||[]).length);

const app={
 querySelector:()=>({onclick:null,addEventListener(){},setAttribute(){}}),
 querySelectorAll:()=>[]
};
const document={querySelector:()=>app};
const ctx={console,window:{addEventListener(){}},document,setTimeout,clearTimeout};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
vm.runInContext(workspace,ctx);
const markup=vm.runInContext(`(()=>{
 const pages=[];
 mount=html=>pages.push(html);
 for(const method of ['renderCompleteness','renderWorkflow','renderQuality','renderIntake','renderPaper','renderSpec','renderMail','renderImpactSimulation','renderOrliReconciliation','renderMaterialReport','renderApprovals','renderSharing']) globalThis[method]=()=>'<article class="preserved-module">Action métier</article>';
 for(const method of ['bindCompleteness','bindWorkflow','bindQuality','bindIntake','bindPaper','bindSpec','bindMail','bindImpactSimulation','bindOrliReconciliation','bindMaterialReport','bindApprovals','bindSharing']) globalThis[method]=()=>{};
 state.me={admin:true,name:'Administrateur démo',permissions:[]};
 state.view='detail';state.folder='jaune';state.detail={
   id:'launch-id',name:'Lancement fictif',status:'En cours',can_update:true,
   folders:['jaune','rose','bleu','vert'].map(slug=>({slug,label:slug,can_read:true,can_write:true,documents:[]}))
 };
 renderDetail();
 return pages[0];
})()`,ctx);
assert(markup.includes('id="detail-tool-workspace"'));
assert(markup.includes('class="detail-tool-nav"'));
assert(markup.includes('class="detail-tool-stage"'));
assert(markup.includes('aria-label="Fonctionnalités du dossier"'));
assert.equal((markup.match(/data-detail-tool="/g)||[]).length,12);
assert.equal((markup.match(/data-detail-tool-panel="/g)||[]).length,12);
assert.equal((markup.match(/class="preserved-module"/g)||[]).length,12);
assert.equal((markup.match(/role="region"/g)||[]).length,12);
assert.equal((markup.match(/data-detail-tool-panel="[^"]+" role="region" aria-label="[^"]+" hidden/g)||[]).length,11);
assert(markup.includes('data-detail-tool="quality" aria-pressed="true"'));
assert(markup.includes('data-detail-tool-panel="quality" role="region" aria-label="Cohérence et Excel"'));
assert(markup.indexOf('simple-document-section')<markup.indexOf('simple-tools'));
for(const [id,label] of [
 ['quality','Cohérence et Excel'],['intake','Lecture et OCR'],['paper','QR et versions'],['spec','Exigences client'],['materials','Suivi matière']]){
 assert(markup.includes('data-detail-tool="'+id+'"'),label+' missing');
}

const buttons=['quality','intake','paper'].map(id=>({
 dataset:{detailTool:id},classList:{toggle(_,on){this.selected=on}},
 setAttribute(key,value){this[key]=value}
}));
const panels=['quality','intake','paper'].map(id=>({dataset:{detailToolPanel:id},hidden:id!=='quality'}));
const title={textContent:''},description={textContent:''},mark={innerHTML:''};
const controls={
 '#detail-tool-stage-title':title,
 '#detail-tool-stage-description':description,
 '.detail-tool-stage-mark':mark
};
const container={
 querySelectorAll(selector){return selector==='[data-detail-tool]'?buttons:panels},
 querySelector(selector){return controls[selector]||null}
};
app.querySelector=selector=>selector==='#detail-tool-workspace'?container:null;
vm.runInContext("selectDetailTool('paper')",ctx);
assert.equal(vm.runInContext('state.detailTool',ctx),'paper');
assert.equal(title.textContent,'QR et versions');
assert.equal(panels[2].hidden,false);
assert.equal(panels[0].hidden,true);
assert.equal(panels[1].hidden,true);
assert.equal(buttons[2]['aria-pressed'],'true');
assert.equal(buttons[0]['aria-pressed'],'false');
assert.equal(mark.innerHTML.includes('<svg'),true);

const detailDisclosure={open:false};
let chosen=null;
const target={scrollIntoView(){this.called=true}};
app.querySelector=selector=>selector==='#detail-tools'?detailDisclosure:(selector==='.spec-section'?target:null);
ctx.selectDetailTool=id=>{chosen=id};
ctx.state.view='detail';
vm.runInContext("focusWorkspaceArea('spec')",ctx);
assert.equal(detailDisclosure.open,true);
assert.equal(chosen,'spec');
assert.equal(target.called,true);

console.log('Framatex 0.28: 12 business modules retained, only one visible, switching works, contextual navigation works.');

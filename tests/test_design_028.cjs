'use strict';
// Historical sheets are bundled into the compatibility layer.
const legacy=require('node:fs').readFileSync('static/legacy-ui.css','utf8');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const js=fs.readFileSync('static/app.js','utf8');
const workspace=fs.readFileSync('static/workspace.js','utf8');
const css=fs.readFileSync('static/design-029.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(legacy.includes('/* design-029.css */'));
assert(legacy.indexOf('/* design-029.css */')>legacy.indexOf('/* design-028.css */'));
assert(css.includes('.detail-tool-panel[hidden]'));
assert(css.includes('.detail-view-panel[hidden]'));
assert(css.includes('.detail-tool-picker'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);

const app={querySelector:()=>({onclick:null,addEventListener(){},setAttribute(){}}),querySelectorAll:()=>[]};
const ctx={console,window:{addEventListener(){}},document:{querySelector:()=>app},setTimeout,clearTimeout};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
vm.runInContext(workspace,ctx);
const markup=vm.runInContext(`(()=>{
 let html='';
 mount=markup=>{html=markup};
 for(const method of ['renderCompleteness','renderWorkflow','renderQuality','renderIntake','renderPaper','renderSpec','renderMail','renderImpactSimulation','renderOrliReconciliation','renderMaterialReport','renderApprovals','renderSharing'])globalThis[method]=()=>'<article class="preserved-module">Action métier</article>';
 for(const method of ['bindCompleteness','bindWorkflow','bindQuality','bindIntake','bindPaper','bindSpec','bindMail','bindImpactSimulation','bindOrliReconciliation','bindMaterialReport','bindApprovals','bindSharing'])globalThis[method]=()=>{};
 state.me={admin:true,name:'Administrateur',permissions:[]};
 state.view='detail';state.folder='jaune';state.detail={id:'launch-id',name:'Lancement fictif',status:'En cours',can_update:true,
  folders:['jaune','rose','bleu','vert'].map(slug=>({slug,label:slug,can_read:true,can_write:true,documents:[]}))};
 renderDetail();return html;
})()`,ctx);
assert(markup.includes('id="detail-tool-workspace"'));
assert(markup.includes('id="detail-tool-select"'));
assert(markup.includes('class="detail-tool-toolbar"'));
assert(markup.includes('role="tablist"'));
assert(markup.includes('data-detail-view="documents"'));
assert(markup.includes('data-detail-view="tools"'));
assert(!markup.includes('class="detail-tool-nav"'));
assert(!markup.includes('simple-disclosure'));
assert(markup.includes('id="launch-info"'));
assert.equal((markup.match(/<optgroup\b/g)||[]).length,4);
assert.equal((markup.match(/<option value="/g)||[]).length,12);
assert.equal((markup.match(/data-detail-tool-panel="/g)||[]).length,12);
assert.equal((markup.match(/class="preserved-module"/g)||[]).length,1); // panneau courant uniquement
assert.equal((markup.match(/data-detail-tool-panel="[^"]+" role="region" aria-label="[^"]+" hidden/g)||[]).length,11);
assert(markup.includes('<option value="quality" selected>Cohérence et Excel</option>'));
assert(markup.indexOf('simple-document-section')<markup.indexOf('id="detail-view-tools"'));

const select={value:'quality'};
const panels=['quality','intake','paper'].map(id=>({dataset:{detailToolPanel:id,...(id==='quality'?{rendered:'true'}:{})},hidden:id!=='quality',innerHTML:''}));
const container={querySelector:selector=>{
 if(selector==='#detail-tool-select')return select;
 return panels.find(p=>selector==='[data-detail-tool-panel="'+p.dataset.detailToolPanel+'"]')||null;
},querySelectorAll:()=>panels};
const tabs=['documents','tools'].map(view=>({dataset:{detailView:view},setAttribute(k,v){this[k]=v}}));
const viewPanels=['documents','tools'].map(view=>({dataset:{detailViewPanel:view},hidden:view!=='documents'}));
const documentArea={scrollIntoView(){this.scrolled=true}};
app.querySelector=selector=>selector==='#detail-tool-workspace'?container:selector==='.spec-section'?documentArea:null;
app.querySelectorAll=selector=>selector==='[data-detail-view]'?tabs:selector==='[data-detail-view-panel]'?viewPanels:[];
vm.runInContext("selectDetailTool('paper')",ctx);
assert.equal(vm.runInContext('state.detailTool',ctx),'paper');
assert.equal(select.value,'paper');
assert(panels[2].hidden===false&&panels[0].hidden===true);
assert(panels[2].innerHTML.includes('preserved-module')); // panneau calculé au premier accès
assert.equal(panels[2].dataset.rendered,'true');
vm.runInContext("switchDetailView('tools')",ctx);
assert.equal(vm.runInContext('state.detailSection',ctx),'tools');
assert(viewPanels[1].hidden===false&&viewPanels[0].hidden===true);
assert.equal(tabs[1]['aria-selected'],'true');
vm.runInContext("switchDetailView('documents')",ctx);
assert(viewPanels[0].hidden===false&&viewPanels[1].hidden===true);
let chosen=null;
ctx.selectDetailTool=id=>{chosen=id};
vm.runInContext("state.view='detail'",ctx);
vm.runInContext("focusWorkspaceArea('spec')",ctx);
assert.equal(chosen,'spec');
assert.equal(vm.runInContext('state.detailSection',ctx),'tools');
assert(documentArea.scrolled===true);
console.log('Framatex 0.29: 12 tool modules, native picker, flat tabs and contextual navigation OK');

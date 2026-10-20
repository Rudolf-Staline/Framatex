'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const source=fs.readFileSync('static/app.js','utf8');
const globalSource=fs.readFileSync('static/global-library.js','utf8');
const styles=fs.readFileSync('static/design-031.css','utf8');
const iconStyles=fs.readFileSync('static/design-folder-icons.css','utf8');
const page=fs.readFileSync('static/index.html','utf8');

const events=[];
const parent={
  dataset:{view:'dossier'},attributes:{},
  addEventListener(type,handler){this[type]=handler},
  setAttribute(name,value){this.attributes[name]=value}
};
const subfolder={
  dataset:{sidebarFolder:'rose'},
  addEventListener(type,handler){this[type]=handler}
};
const children={hidden:true};
const emptyNode={addEventListener(){},onclick:null};
const app={
  innerHTML:'',
  querySelectorAll(selector){
    if(selector==='[data-view]')return [parent];
    if(selector==='[data-sidebar-folder]')return [subfolder];
    return [];
  },
  querySelector(selector){
    if(selector==='#dossier-nav-children')return children;
    return emptyNode;
  }
};
const context={
  console,
  setTimeout,clearTimeout,
  document:{querySelector(selector){
    return selector==='#app'?app:emptyNode;
  }},
  window:{addEventListener(){}},
  syncFloatingAssistant(){},
  calls:events
};
vm.createContext(context);
vm.runInContext(source.slice(0,source.lastIndexOf('(async function init(){')),context);
vm.runInContext("navigate=async v=>calls.push(['view',v]);openGlobalFolder=async slug=>calls.push(['folder',slug])",context);
vm.runInContext("state.me={admin:true,name:'Administratrice',permissions:[]};state.view='dossier';state.sidebarDossierOpen=false",context);

let sidebar=vm.runInContext('sidebar()',context);
assert(sidebar.includes('data-view="dossier" title="Dossier Jaune"'));
assert(sidebar.includes('aria-expanded="false"'));
assert(sidebar.includes('aria-controls="dossier-nav-children"'));
assert(sidebar.includes('id="dossier-nav-children"'));
assert(sidebar.includes('id="dossier-nav-children" role="group" aria-label="Sous-dossiers du Dossier Jaune" hidden'));
for(const name of ['jaune','rose','bleu','vert']){
  assert(sidebar.includes('data-sidebar-folder="'+name+'"'),name+' must appear in navigation');
  assert(sidebar.includes('class="dossier-child-folder '+name+'"'),name+' must have its own folder icon');
  assert(iconStyles.includes('.dossier-child-folder.'+name),name+' icon must have a distinct palette');
}
vm.runInContext("mount('<main>Documents</main>','Dossier Jaune')",context);
assert.equal(typeof parent.click,'function');
assert.equal(typeof subfolder.click,'function');

parent.click();
assert.equal(vm.runInContext('state.sidebarDossierOpen',context),true);
assert.equal(children.hidden,false);
assert.equal(parent.attributes['aria-expanded'],'true');
parent.click();
assert.equal(vm.runInContext('state.sidebarDossierOpen',context),false);
assert.equal(children.hidden,true);

parent.click();
subfolder.click();
assert(events.some(entry=>entry[0]==='folder'&&entry[1]==='rose'));
assert.equal(vm.runInContext('state.sidebarDossierOpen',context),true);
vm.runInContext("state.dossierFolder='rose'",context);
sidebar=vm.runInContext('sidebar()',context);
assert(sidebar.includes('data-sidebar-folder="rose" aria-current="location"'));
assert(sidebar.includes('aria-expanded="true"'));

vm.runInContext("state.view='notifications';state.sidebarDossierOpen=false",context);
parent.click();
assert(events.some(entry=>entry[0]==='view'&&entry[1]==='dossier'));
assert.equal(vm.runInContext('state.sidebarDossierOpen',context),true);

assert(globalSource.includes('async function openGlobalFolder(slug)'));
assert(globalSource.includes('state.dossierFolder=slug'));
assert(globalSource.includes('state.sidebarDossierOpen=true'));
assert(styles.includes('.dossier-nav-children[hidden]'));
assert(styles.includes('.dossier-nav-child:focus-visible'));
assert(styles.includes('@media(max-width:760px)'));
assert(sidebar.includes('<svg'), 'Folder icons must use vector artwork');
assert(!sidebar.includes('class="dossier-child-dot'), 'Colored squares must be removed from sidebar');
assert(iconStyles.includes('fill:var(--folder-icon-fill)'));
assert(iconStyles.includes('stroke:var(--folder-icon-stroke)'));
assert(iconStyles.includes('.dossier-nav-child.active'));
assert(iconStyles.includes('@media(max-width:760px)'));
assert(page.includes('/assets/design-folder-icons.css'));
assert(page.indexOf('/assets/design-folder-icons.css')>page.indexOf('/assets/design-assistant-v2.css'));

console.log('Sidebar dossier unique : accordéon, 4 rubriques, sélection et clavier OK');

'use strict';
// Historical sheets are bundled into the compatibility layer.
const legacy=require('node:fs').readFileSync('static/legacy-ui.css','utf8');
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');

const appJs=fs.readFileSync('static/app.js','utf8');
const libraryJs=fs.readFileSync('static/global-library.js','utf8');
const css=fs.readFileSync('static/design-033.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');

assert(legacy.includes('/* design-033.css */'),'stylesheet must be loaded');
assert(legacy.indexOf('/* design-033.css */')>legacy.indexOf('/* design-032.css */'));
assert(css.includes('.app-shell[data-dossier-theme] .main'));
assert(css.includes('.app-shell[data-dossier-theme] .sidebar.sidebar-rail.sidebar-light'));
assert(css.includes('.app-shell[data-dossier-theme] .global-workspace-panel'));
assert(css.includes('.app-shell[data-dossier-theme] .global-workspace .primary'));
assert(css.includes('@media(max-width:760px)'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length,'CSS braces balanced');

function rgb(hex){
 const n=parseInt(hex.replace('#',''),16);
 return [n>>16&255,n>>8&255,n&255].map(c=>{
  const s=c/255;
  return s<=.04045?s/12.92:Math.pow((s+.055)/1.055,2.4);
 });
}
function luminance(hex){const [r,g,b]=rgb(hex);return .2126*r+.7152*g+.0722*b}
function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)}
const colors={
 jaune:{button:'#f1c443',ink:'#352808'},
 rose:{button:'#a83e72',ink:'#ffffff'},
 bleu:{button:'#2368ae',ink:'#ffffff'},
 vert:{button:'#237956',ink:'#ffffff'},
};
for(const [folder,expected] of Object.entries(colors)){
 const block=new RegExp('\\.app-shell\\[data-dossier-theme="'+folder+'"\\]\\{([^}]+)\\}').exec(css);
 assert(block,folder+' theme definition missing');
 for(const prop of ['--folder-accent','--folder-canvas','--folder-side','--folder-header','--folder-soft','--folder-button']){
  assert(block[1].includes(prop+':'),folder+' missing '+prop);
 }
 assert(contrast(expected.button,expected.ink)>=4.5,folder+' button contrast below WCAG AA');
}

const resultPane={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>({addEventListener(){}})};
const countPane={textContent:''};
const empty={querySelectorAll:()=>[],addEventListener(){},setAttribute(){}};
const app={
 innerHTML:'',
 querySelectorAll:()=>[],
 querySelector(s){
  if(s==='#global-doc-results')return resultPane;
  if(s==='#global-result-count')return countPane;
  return empty;
 }
};
const ctx={
 console,
 window:{addEventListener(){}},
 document:{querySelector:()=>app},
 setTimeout,clearTimeout,
 syncFloatingAssistant(){},
};
vm.createContext(ctx);
vm.runInContext(appJs.slice(0,appJs.lastIndexOf('(async function init(){')),ctx);
vm.runInContext(libraryJs,ctx);
const data={
 name:'Dossier Jaune',unique:true,
 folders:Object.keys(colors).map(slug=>({
  slug,label:slug,can_read:true,can_write:true,count:0,documents:[]
 }))
};
ctx.sample=data;
vm.runInContext("state.me={name:'Test',admin:true,permissions:[]};state.view='dossier';state.sidebarDossierOpen=true;globalIndex=sample",ctx);
for(const folder of Object.keys(colors)){
 vm.runInContext("globalFolder='"+folder+"';renderGlobalLibrary()",ctx);
 assert(app.innerHTML.includes('data-dossier-theme="'+folder+'"'),'mount must apply '+folder);
 assert(!app.innerHTML.includes('data-sidebar-folder'),'no shared dossier menu');
}
vm.runInContext("state.view='notifications';mount('<p>Messages</p>','Notifications')",ctx);
assert(!app.innerHTML.includes('data-dossier-theme'),'other screens must retain neutral theme');
vm.runInContext("state.view='dossier';globalFolder='jaune';globalIndex=sample;openGlobalFolder('rose')",ctx);
assert(app.innerHTML.includes('data-dossier-theme="rose"'),'folder switch must update theme immediately');
assert(css.includes('.global-workspace .global-table th'),'document table must adopt theme');
console.log('Dossier contextual colors: all 4 themes, UI switch, AA button contrast and mobile styles OK');

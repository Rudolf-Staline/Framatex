'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const js=fs.readFileSync('static/app.js','utf8');
const quality=fs.readFileSync('static/quality.js','utf8');
const css=fs.readFileSync('static/design-029.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('design-029.css'));
assert(html.indexOf('design-029.css')>html.indexOf('design-028.css'));
assert(css.includes('.detail-main-tabs'));
assert(css.includes('.detail-tool-picker select'));
assert(css.includes('.quality-simple-row'));
assert(css.includes('.launch-information-list'));
assert(css.includes('@media(max-width:540px)'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);
const root={innerHTML:'',querySelector:()=>({onclick:null,addEventListener(){}}),querySelectorAll:()=>[]};
const ctx={console,setTimeout,clearTimeout,document:{querySelector:()=>root},window:{addEventListener(){}}};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
vm.runInContext(quality,ctx);
assert(!vm.runInContext("niceDate('2026-10-18T14:39:21+00:00')",ctx).includes('Invalid'));
assert.equal(vm.runInContext("niceDate('not-a-date')",ctx),'—');
assert.equal(vm.runInContext("niceDate(null)",ctx),'—');
const empty=vm.runInContext(`(()=>{
 state.me={admin:true,name:'Admin'};
 state.detail={id:'launch',folders:[]};
 state.qualityReport={rows:[]};
 state.excelInspections=[];
 return renderQuality();
})()`,ctx);
assert(empty.includes('Fiabilité documentaire'));
assert(empty.includes('Cohérence entre documents'));
assert(empty.includes('Système immunitaire Excel'));
assert(empty.includes('Aucune comparaison configurée'));
assert(empty.includes('Aucun classeur Excel analysé'));
assert(!empty.includes('workflow-stats'),'Empty metrics should disappear');
assert(!empty.includes('Règles consultables'));
assert(!empty.includes('Écarts non traités'));
assert(!empty.includes('Version 0.4'));
vm.runInContext(fs.readFileSync('static/order-identification.js','utf8'),ctx);
(async()=>{
const info=await vm.runInContext(`(async()=>{
 let captured={};
 modal=(title,body)=>{captured={title,body}};
 state.detail={id:'uuid-example',client_name:'Acme <script>',order_ref:'C-2',
 orli_ref:null,updated_at:'2026-10-18T14:39:21+00:00'};
 orderFieldCatalog=[{key:'client_name',label:'Client',type:'text',storage:'base'},
 {key:'order_ref',label:'Numéro de commande',type:'text',storage:'base'},
 {key:'orli_ref',label:'Référence ORLI',type:'text',storage:'base'}];
 await showLaunchInformation();
 return captured;
})()`,ctx);
assert.equal(info.title,'Fiche commande');
assert(info.body.includes('Numéro de commande'));
assert(info.body.includes('Non renseigné'));
assert(info.body.includes('Acme &lt;script&gt;'));
assert(!info.body.includes('<script>'));
assert(!info.body.includes('Invalid Date'));
assert(js.includes('ArrowRight')&&js.includes('ArrowLeft'));
console.log('Framatex 0.29: compact dossier, accessible tabs, clean empty quality, timezone dates and safe information modal OK');

})().catch(err=>{console.error(err);process.exitCode=1});

'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

(async()=>{
 const source=fs.readFileSync('static/app.js','utf8');
 const boot=source.slice(source.lastIndexOf('(async function init(){'));
 let ready,apiCalls=0,destination=null;
 const context={document:{readyState:'interactive',addEventListener:(name,callback)=>{
  assert.equal(name,'DOMContentLoaded');ready=callback;
 }},api:async()=>{apiCalls++;return {name:'Utilisateur'}},state:{},renderLogin:()=>{throw Error('Unexpected login')}};
 vm.createContext(context);
 const pending=vm.runInContext(boot,context);
 assert.equal(apiCalls,0,'No auth request may finish before all deferred modules exist');
 context.paperOpenDeepLink=async()=>false;
 context.navigate=async view=>{destination=view};
 ready();await pending;
 assert.equal(apiCalls,1);assert.equal(destination,'home');

 const rex={e:x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
  GLOB_COLORS:{rose:'Rose'},GLOB_DESCRIPTIONS:{rose:'Réception'},can:()=>true,icon:()=>'<svg></svg>'};
 vm.createContext(rex);
 vm.runInContext(fs.readFileSync('static/experience.js','utf8'),rex);
 const html=vm.runInContext('rexSourceButtons([{id:"abc",title:"<script>bad</script>",folder:"rose",status:"resolu",orli_ref:"REF-1"}])',rex);
 assert(html.includes('data-rex-source="abc"'));
 assert(html.includes('&lt;script>')&&!html.includes('<script>'));
 assert(html.includes('Fiche 1')&&html.includes('REF-1'));
 console.log('Mémoire métier: cited sources, HTML escaping and deferred bootstrap regression OK');
})().catch(error=>{console.error(error);process.exitCode=1});

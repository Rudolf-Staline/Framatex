'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const pending=[];
 const ctx=vm.createContext({console,Promise,URLSearchParams,setTimeout,clearTimeout,
  api:path=>new Promise(resolve=>pending.push({path,resolve})),
  mount:()=>{throw new Error('Stale dossier overwrote the current screen');},
  state:{view:'admin',me:{admin:true}},
 });
 vm.runInContext('let navigationVersion=1;',ctx);
 vm.runInContext(fs.readFileSync('static/orders.js','utf8'),ctx);
 const loading=vm.runInContext("orderDossierPage('synthetic-order')",ctx);
 assert.equal(pending.length,3); // dossier, summary order and completeness
 vm.runInContext("++navigationVersion;state.view='admin'",ctx);
 for(const p of pending)p.resolve({id:'synthetic-order',reference:'Synthetic',sections:[],launches:[],items:[]});
 await loading;
 assert.equal(vm.runInContext('state.view',ctx),'admin');
 // Pagination buttons inside business forms must never be mistaken for submit.
 let complete;
 const waiting=new Promise(resolve=>{complete=resolve});
 const submit={disabled:false};let handler;
 const formNode={querySelector:()=>{throw new Error('Submitter ignored');}};
 const forms=vm.createContext({$:()=>({set onsubmit(value){handler=value}}),run:action=>action(),
  FormData:class{*[Symbol.iterator](){}}});
 vm.runInContext(fs.readFileSync('static/partners.js','utf8').split('\n').find(line=>line.startsWith('function form(')),forms);
 forms.action=()=>waiting;vm.runInContext("form('request',action)",forms);
 handler({preventDefault(){},target:formNode,submitter:submit});assert.equal(submit.disabled,true);
 complete();await new Promise(resolve=>setImmediate(resolve));assert.equal(submit.disabled,false);
 console.log('Canonical dossier: a late initial response preserves later navigation.');
})().catch(error=>{console.error(error);process.exitCode=1;});

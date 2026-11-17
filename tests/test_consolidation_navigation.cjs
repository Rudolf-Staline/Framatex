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
 console.log('Canonical dossier: a late initial response preserves later navigation.');
})().catch(error=>{console.error(error);process.exitCode=1;});

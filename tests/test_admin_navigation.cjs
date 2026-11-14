'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/app.js','utf8');
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve}};
function context(){
 const events={};
 const ctx={document:{querySelector:()=>({}),addEventListener:(name,fn)=>{events[name]=fn}},window:{addEventListener:()=>{}},console,setTimeout,clearTimeout};
 vm.createContext(ctx);return {ctx,events};
}
(async()=>{
 // The real bootstrap must not authenticate or call feature globals until the
 // deferred scripts are ready; define paperOpenDeepLink only after app.js runs.
 const {ctx,events}=context();
 const startup=vm.runInContext(source,ctx);
 vm.runInContext(`globalThis.calls=[];api=async path=>{calls.push(path);return {admin:true}};
  globalThis.paperOpenDeepLink=async()=>{calls.push('paper');return false};
  navigate=async view=>calls.push(view);`,ctx);
 assert.deepEqual(Array.from(ctx.calls),[]);
 events.DOMContentLoaded();await startup;
 assert.deepEqual(Array.from(ctx.calls),['/api/auth/me','paper','home']);

 for(const phase of ['detail','supplier-requests']){
  const {ctx}=context();const gate=deferred(),entered=deferred();
  ctx.gate=gate;ctx.entered=entered;ctx.phase=phase;
  vm.runInContext(source.slice(0,source.lastIndexOf('(async function init(){')),ctx);
  vm.runInContext(`state.me={admin:true};state.clientPublications=['keep'];
   globalThis.renders=[];
   api=async path=>{
    const held=phase==='detail'?path==='/api/launches/old':path.endsWith('/supplier-requests');
    if(held){entered.resolve();return gate.promise}return [];
   };
   renderDetail=()=>renders.push(state.detail);
   admin=async()=>{state.view='admin'};
   globalThis.refresh=openLaunch('old');`,ctx);
  await entered.promise;
  await vm.runInContext("navigate('admin')",ctx);
  gate.resolve({id:'old'});await ctx.refresh;
  assert.equal(vm.runInContext('state.view',ctx),'admin',phase);
  assert.deepEqual(Array.from(ctx.renders),[],phase);
  assert.deepEqual(Array.from(vm.runInContext('state.clientPublications',ctx)),['keep'],phase);
  // A subsequent intentional dossier navigation must still render normally.
  vm.runInContext("api=async path=>path==='/api/launches/current'?{id:'current'}:[]",ctx);
  await vm.runInContext("openLaunch('current')",ctx);
  assert.equal(ctx.renders.length,1);
  assert.equal(ctx.renders[0].id,'current');
 }
 console.log('Administration: deferred startup and stale dossier responses in both loading phases OK');
})().catch(error=>{console.error(error);process.exitCode=1});

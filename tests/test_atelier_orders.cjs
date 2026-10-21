'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
// Run the actual listing handlers against a minimal DOM; data contains homonymous clients.
const nodes=new Map();
function node(id){if(!nodes.has(id))nodes.set(id,{innerHTML:'',value:'',textContent:'',disabled:false,handlers:{},addEventListener(name,fn){this.handlers[name]=fn},querySelectorAll(){return []}});return nodes.get(id)}
const app={querySelector:node,querySelectorAll:()=>[]};
const sample=Array.from({length:12},(_,i)=>({id:'L'+i,name:i===0?'Étoffe été <script>':'Commande '+i,client_id:i===11?'other':'alpha',client_name:'Même société',order_ref:'CMD-'+i,status:i%2?'En cours':'À compléter',identification:{delivery_date:i===0?null:'2026-11-'+String(i+1).padStart(2,'0')},updated_at:'2026-10-'+String(i+1).padStart(2,'0')}));
const context={console,document:{addEventListener(){}},state:{query:'',clientFilter:{id:'alpha',name:'Même société'},me:{admin:true}},app,api:async()=>sample,mount(){},can:()=>true,icon:()=>'<svg></svg>',e:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),niceDate:x=>x||'—',statusTag:s=>s,showErr:err=>{throw err}};
vm.createContext(context);vm.runInContext(fs.readFileSync('static/order-identification.js','utf8'),context);
(async()=>{
 await vm.runInContext('orderListPage()',context);
 assert.equal(node('#order-count').textContent,'1–10 sur 11 dossiers');
 assert(!node('#orders-table').innerHTML.includes('data-order-open="L11"'),'same name must not expose another client’s orders');
 node('#orders-next').onclick();assert.equal(node('#order-count').textContent,'11–11 sur 11 dossiers');assert(node('#orders-next').disabled);
 node('#order-search').handlers.input({target:{value:'etoffe'}});
 assert(node('#orders-table').innerHTML.includes('Étoffe été &lt;script>'));
 assert(!node('#orders-table').innerHTML.includes('<script>'));
 assert.equal(node('#order-count').textContent,'1–1 sur 1 dossier');
 node('#order-search').handlers.input({target:{value:'introuvable'}});assert.equal(node('#order-count').textContent,'Aucun résultat');
 node('#order-search').handlers.input({target:{value:''}});node('#order-sort').value='delivery';node('#order-sort').handlers.change();
 assert(!node('#orders-table').innerHTML.includes('data-order-open="L0"'),'undated dossiers must sort after dated dossiers');
 node('#orders-next').onclick();assert(node('#orders-table').innerHTML.includes('data-order-open="L0"'));
 const html=fs.readFileSync('static/index.html','utf8'),css=fs.readFileSync('static/atelier.css','utf8');
 assert.equal((html.match(/rel="stylesheet"/g)||[]).length,2);
 assert(css.includes('prefers-reduced-motion'));assert(css.includes('@font-face'));
 console.log('Atelier: exact client filters, accents, escaping, paging, missing-date sorting and stylesheet loading OK');
})().catch(err=>{console.error(err);process.exitCode=1});
// A calendar date must not move to the previous day in a negative UTC offset.
const originalTZ=process.env.TZ;process.env.TZ='America/Los_Angeles';
const code=fs.readFileSync('static/app.js','utf8');const dateContext={};vm.createContext(dateContext);
vm.runInContext(code.slice(code.indexOf('function niceDate('),code.indexOf('\nfunction sizeText(')),dateContext);
assert.match(vm.runInContext("niceDate('2026-11-05')",dateContext),/^05/);
if(originalTZ===undefined)delete process.env.TZ;else process.env.TZ=originalTZ;

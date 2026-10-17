'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('static/impact_sim.js','utf8');
const ctx={console,Intl,Number};vm.createContext(ctx);vm.runInContext(src,ctx);
ctx.e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
ctx.can=()=>true;
ctx.state={simHistory:[],simGraph:{nodes:[
  {id:'quantite_lancement',label:'Quantité <script>x</script>',kind:'input',unit:'pièce',available:true,value:'1500'},
  {id:'besoin_calcule',label:'Besoin',kind:'derived',unit:'m',available:true,value:'2700'}],
  edges:[{source:'quantite_lancement',target:'besoin_calcule',meaning:'Multiplication',kind:'formula'}],limited:false}};
const html=vm.runInContext('renderImpactSimulation()',ctx);
assert(html.includes('Simulation'));
assert(html.includes('sim-form'));
assert(html.includes('&lt;script&gt;'));
assert(!html.includes('<script>'));
ctx.state.simGraph={nodes:[],edges:[],limited:true};
const deny=vm.runInContext('renderImpactSimulation()',ctx);
assert(!deny.includes('sim-form'));
assert(deny.includes('réservé'));
const output=vm.runInContext('simResultsHtml({outputs:[{label:"Coût <img>",unit:"MAD",baseline:"100",scenario:"110",delta:"10"}],warnings:["Essai <svg>"]})',ctx);
assert(!output.includes('<img>')&&!output.includes('<svg>'));
assert(output.includes('+10'));
console.log('Frontend 0.10 : vue graphe, simulation, confidentialité et échappement OK');

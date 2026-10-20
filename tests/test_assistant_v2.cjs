'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('static/index.html','utf8');
const src=fs.readFileSync('static/floating-assistant.js','utf8');
const css=fs.readFileSync('static/design-assistant-v2.css','utf8');
assert(html.includes('/assets/design-assistant-v2.css'));
assert(html.indexOf('/assets/design-assistant-v2.css')>html.indexOf('/assets/design-cleanup.css'));
assert(css.includes('.floating-assistant-suggestions button'));
assert(css.includes('.floating-assistant-form textarea'));
assert(css.includes('textarea:focus'));
assert(css.includes('.floating-assistant-compose-hint'));
assert(css.includes('max-width:620px'));
assert(css.includes('prefers-reduced-motion'));
assert(css.includes('env(safe-area-inset-bottom)'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);
assert(!src.includes('title="Fermer"'), 'Remove ugly native close tooltip');
assert(!src.includes("'>',icon('plus'),'</button>'"),'No reset plus in the header');
assert(src.includes('aria-label="Nouvelle discussion"'));
assert(src.includes('aria-label="Fermer l’assistant"'));
assert(src.includes('aria-label="Posez votre question"'));
assert(src.includes("if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing)"));
assert(src.includes("FLOATING_QUESTIONS.map((q,i)"));
assert(src.includes('floating-assistant-suggestion-icon'));
assert(src.includes('floating-assistant-suggestion-label'));

const listeners={};
const reset={hidden:true,addEventListener(t,fn){listeners.reset=fn},focus(){}};
const input={value:'',disabled:false,scrollHeight:50,style:{},focus(){},addEventListener(t,fn){listeners['input_'+t]=fn}};
const send={disabled:false};
const close={addEventListener(t,fn){listeners.close=fn}};
const chat={innerHTML:'',scrollHeight:0,scrollTop:0,querySelectorAll:()=>[]};
const trigger={setAttribute(){},addEventListener(){}};
const panel={hidden:true,querySelectorAll:()=>[close,reset,input,send]};
const backdrop={hidden:true,addEventListener(){}};
const form={addEventListener(t,fn){listeners.form=fn}};
const root={
 dataset:{},
 hidden:false,
 innerHTML:'',
 classList:{add(){},remove(){}},
 querySelector(sel){
  return {
   '#floating-assistant-reset':reset,
   '#floating-assistant-close':close,
   '#floating-assistant-input':input,
   '#floating-assistant-send':send,
   '#floating-assistant-trigger':trigger,
   '#floating-assistant-panel':panel,
   '#floating-assistant-backdrop':backdrop,
   '#floating-assistant-chat':chat,
   '#floating-assistant-form':form
  }[sel]||null;
 }
};
const ctx={
 console,
 state:{me:{name:'Test'},view:'dossier',folder:'jaune'},
 document:{querySelector:s=>s==='#floating-assistant-root'?root:null,activeElement:trigger,
  addEventListener(){},removeEventListener(){}},
 overlay:{querySelector:()=>null},
 icon:name=>'<svg class="ui-icon" data-type="'+name+'"></svg>',
 e:text=>String(text).replace(/[&<>"']/g,t=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[t])),
 api:async()=>({title:'Document disponible',answer:'Voici le résultat'}),
 showErr:err=>{throw err},
 openGlobalFolder:async()=>{},navigate:async()=>{},focusWorkspaceArea:()=>{}
};
vm.createContext(ctx);vm.runInContext(src,ctx);
vm.runInContext('buildFloatingAssistant()',ctx);
assert(root.innerHTML.includes('ASSISTANCE DOCUMENTAIRE'));
assert(root.innerHTML.includes('floating-assistant-compose-hint'));
assert(root.innerHTML.includes('floating-assistant-suggestion-arrow'));
assert(root.innerHTML.includes('rows="1"'));
assert(!root.innerHTML.includes('title="Fermer"'));
assert(!root.innerHTML.includes('Nouvelle conversation'));
vm.runInContext('paintFloatingAssistant()',ctx);
assert.equal(reset.hidden,true);
assert(chat.innerHTML.includes('Comment puis-je vous aider ?'));
assert.equal((chat.innerHTML.match(/class="floating-assistant-suggestion"/g)||[]).length,3);
assert(chat.innerHTML.includes('Trouver une solution déjà utilisée'));
assert(chat.innerHTML.includes('Consulter une procédure'));
vm.runInContext("floatingAssistantMessages.push({kind:'user',text:'Question'})",ctx);
vm.runInContext('paintFloatingAssistant()',ctx);
assert.equal(reset.hidden,false);
assert(!chat.innerHTML.includes('Comment puis-je vous aider ?'));
listeners.reset();
assert.equal(reset.hidden,true);
assert(chat.innerHTML.includes('Comment puis-je vous aider ?'));
console.log('Assistant Framatex V2: style, accessible cards, clean textarea and reset-after-conversation OK');

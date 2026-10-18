'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('static/floating-assistant.js','utf8');
const app=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-023.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('id="floating-assistant-root" hidden'));
assert(html.includes('/assets/floating-assistant.js'));
assert(html.includes('/assets/design-023.css'));
assert(html.indexOf('design-023.css')>html.indexOf('design-022.css'));
assert(app.includes('syncFloatingAssistant()'));
assert(!app.includes("['assistant','layers','Assistant']"));
assert(src.includes('aria-modal="true"'));
assert(src.includes('aria-expanded="false"'));
assert(src.includes('id="floating-assistant-reset"'));
assert(css.includes('position:fixed')&&css.includes('prefers-reduced-motion'));
assert(css.includes('@media(max-width:620px)'));
assert(css.includes('env(safe-area-inset-bottom)'));
assert(css.includes(':focus-visible'));

const attributes={};
const trigger={setAttribute(k,v){attributes[k]=v},focus(){},isConnected:true};
const chat={innerHTML:'',scrollHeight:100,scrollTop:0,
 querySelectorAll(){return []}};
const input={value:'',disabled:false,focus(){this.focused=true}};
const send={disabled:false};
const panel={hidden:true,querySelectorAll(){return [trigger,input]}};
const backdrop={hidden:true};
const els={
 '#floating-assistant-trigger':trigger,
 '#floating-assistant-panel':panel,
 '#floating-assistant-backdrop':backdrop,
 '#floating-assistant-chat':chat,
 '#floating-assistant-input':input,
 '#floating-assistant-send':send
};
const classes=new Set();
const host={dataset:{ready:'1'},hidden:true,
 classList:{add(k){classes.add(k)},remove(k){classes.delete(k)}},
 querySelector(k){return els[k]||null}};
const keyboard={};
const document={
 activeElement:trigger,
 querySelector(k){return k==='#floating-assistant-root'?host:null},
 addEventListener(type,fn){keyboard[type]=fn},
 removeEventListener(type){delete keyboard[type]}
};
const ctx={console,document,overlay:{querySelector:()=>null},
 state:{me:null,view:'home',detail:null,folder:'jaune'},
 icon:()=>'<svg></svg>',
 e:x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 showErr:err=>{throw err},
 openLaunch:async()=>{},navigate:async()=>{},focusWorkspaceArea:()=>{}
};
ctx.api=async(path,options)=>{
 ctx.lastCall={path,options};
 return {title:'Procédure <script>',answer:'Réponse documentée',source:'Guide interne',destination:'launches'};
};
vm.createContext(ctx);vm.runInContext(src,ctx);
(async()=>{
 vm.runInContext('syncFloatingAssistant()',ctx);
 assert.equal(host.hidden,true,'The unauthenticated launcher must not render');
 ctx.state.me={name:'Utilisateur',admin:false};
 ctx.state.view='detail';ctx.state.detail={id:'la-123'};
 vm.runInContext('syncFloatingAssistant()',ctx);
 assert.equal(host.hidden,false,'Authenticated users get assistant access');
 vm.runInContext('openFloatingAssistant()',ctx);
 assert.equal(panel.hidden,false);
 assert.equal(backdrop.hidden,false);
 assert.equal(attributes['aria-expanded'],'true');
 assert.equal(input.focused,true);
 await vm.runInContext("askFloatingAssistant('Facture <script>alert(1)</script>')",ctx);
 assert.equal(ctx.lastCall.path,'/api/assistant/guide');
 const payload=JSON.parse(ctx.lastCall.options.body);
 assert.equal(payload.launch_id,'la-123');
 assert.equal(payload.question,'Facture <script>alert(1)</script>');
 assert(!chat.innerHTML.includes('<script>'),'Assistant output must be escaped');
 assert(chat.innerHTML.includes('&lt;script&gt;'));
 assert(chat.innerHTML.includes('Réponse documentée'));
 assert(chat.innerHTML.includes('floating-assistant-follow'));
 vm.runInContext('closeFloatingAssistant()',ctx);
 assert.equal(panel.hidden,true);
 assert.equal(attributes['aria-expanded'],'false');
 vm.runInContext('openFloatingAssistant()',ctx);
 assert(chat.innerHTML.includes('Réponse documentée'),'History persists after reopen');
 keyboard.keydown({key:'Escape',preventDefault(){}});
 assert.equal(panel.hidden,true,'Escape must close the panel');
 ctx.state.me=null;
 vm.runInContext('syncFloatingAssistant()',ctx);
 assert.equal(host.hidden,true,'Logout must hide and reset the panel');
 assert(!vm.runInContext('floatingAssistantMessages.length',ctx));
 console.log('Framatex Assist 0.23: premium panel, auth, context, XSS, history, ESC, mobile CSS OK');
})().catch(err=>{console.error(err);process.exitCode=1});

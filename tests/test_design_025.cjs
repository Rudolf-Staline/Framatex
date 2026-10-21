'use strict';
// Historical sheets are bundled into the compatibility layer.
const legacy=require('node:fs').readFileSync('static/legacy-ui.css','utf8');
const fs=require('node:fs'), vm=require('node:vm'),assert=require('node:assert/strict');
const js=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-026.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(legacy.includes('/* design-024.css */'));
assert(legacy.includes('/* design-026.css */'));
assert(legacy.indexOf('/* design-026.css */')>legacy.indexOf('/* design-024.css */'));
assert(css.includes('.login-page.login-rebalanced'));
assert(css.includes('grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr)'));
assert(css.includes('.login-rebalanced .login-visual'));
assert(css.includes('background:#fff'));
assert(css.includes('@media(max-width:620px)'));
assert(css.includes('.login-rebalanced .login-visual{display:none}'));
const form={addEventListener(type,handler){this.submitType=type;this.onSubmit=handler}};
const controls={focus(){},addEventListener(){}};
const app={innerHTML:'',querySelectorAll(){return []},
 querySelector(selector){return selector==='#login-form'?form:controls}};
const overlay={innerHTML:'unchanged'};
const ctx={console,setTimeout,clearTimeout,window:{addEventListener(){}},
 document:{querySelector(selector){if(selector==='#app')return app;if(selector==='#overlay-root')return overlay;return {}}}};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
vm.runInContext('syncFloatingAssistant=()=>{};icon=()=>"<svg></svg>";renderLogin()',ctx);
assert(app.innerHTML.includes('id="space-title"'));
assert(app.innerHTML.includes('data-space="internal"')&&app.innerHTML.includes('data-space="client"'));
assert.equal((app.innerHTML.match(/<form\b/g)||[]).length,0);
for(const space of ['internal','client']){
 vm.runInContext('renderLogin("'+space+'")',ctx);
 const output=app.innerHTML;
 assert.equal(overlay.innerHTML,'');
 assert.equal((output.match(/<form\b/g)||[]).length,1);
 assert.equal((output.match(/<input\b/g)||[]).length,2);
 assert(output.includes('id="change-space"'));
 assert(output.includes('id="login-error"'));
 assert(output.includes('for="email"')&&output.includes('for="password"'));
 assert(output.includes('autocomplete="username"')&&output.includes('autocomplete="current-password"'));
 assert(output.includes('ESPACE '+(space==='client'?'CLIENT':'INTERNE')));
 assert.equal(form.submitType,'submit');
}
console.log('Space selection precedes login; both spaces retain labeled credential forms and a back action.');

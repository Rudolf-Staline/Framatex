'use strict';
const fs=require('node:fs'), vm=require('node:vm'),assert=require('node:assert/strict');
const js=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-024.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('/assets/design-024.css'));
assert(css.includes('.login-page.login-minimal'));
assert(css.includes('.login-minimal .login-form-wrap'));
assert(css.includes('background:#fff'));

const form={addEventListener(type,handler){this.submitType=type;this.onSubmit=handler}};
const app={innerHTML:'',
 querySelector(selector){if(selector==='#login-form')return form;throw Error('Unexpected selector '+selector)}};
const overlay={innerHTML:'unchanged'};
const ctx={console,setTimeout,clearTimeout,
 window:{addEventListener(){}},
 document:{querySelector(selector){if(selector==='#app')return app;if(selector==='#overlay-root')return overlay;return {}}}};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
vm.runInContext('syncFloatingAssistant=()=>{};renderLogin()',ctx);
const output=app.innerHTML;
assert.equal(overlay.innerHTML,'');
assert.equal((output.match(/<form\b/g)||[]).length,1);
assert.equal((output.match(/<input\b/g)||[]).length,2);
assert.equal((output.match(/<button\b/g)||[]).length,1);
assert(output.includes('class="login-page login-minimal"'));
assert(output.includes('<main class="login-form-wrap">'));
assert(output.includes('id="login-error"'));
assert(output.includes('for="email"')&&output.includes('for="password"'));
assert(output.includes('autocomplete="username"')&&output.includes('autocomplete="current-password"'));
assert(output.includes('type="submit">Se connecter</button>'));
assert.equal(form.submitType,'submit');
for(const removed of ['login-art','login-hero','login-caption','UNE NOUVELLE MANIÈRE','Chaque lancement','Bienvenue','Connectez-vous','ACCÈS SÉCURISÉ','prototype','administrateur','Dossier jaune numérique','Gestion documentaire']){
 assert(!output.includes(removed),'Redundant login text remains: '+removed);
}
assert((css.match(/\{/g)||[]).length===(css.match(/\}/g)||[]).length);
console.log('Framatex 0.25: login contains only two fields, validation feedback and submit action.');

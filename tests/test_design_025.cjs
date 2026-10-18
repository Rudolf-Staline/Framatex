'use strict';
const fs=require('node:fs'), vm=require('node:vm'),assert=require('node:assert/strict');
const js=fs.readFileSync('static/app.js','utf8');
const css=fs.readFileSync('static/design-026.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
assert(html.includes('/assets/design-024.css'));
assert(html.includes('/assets/design-026.css'));
assert(html.indexOf('design-026.css')>html.indexOf('design-024.css'));
assert(css.includes('.login-page.login-rebalanced'));
assert(css.includes('grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr)'));
assert(css.includes('.login-rebalanced .login-visual'));
assert(css.includes('background:#fff'));
assert(css.includes('@media(max-width:620px)'));
assert(css.includes('.login-rebalanced .login-visual{display:none}'));
const form={addEventListener(type,handler){this.submitType=type;this.onSubmit=handler}};
const app={innerHTML:'',
 querySelector(selector){if(selector==='#login-form')return form;throw Error('Unexpected selector '+selector)}};
const overlay={innerHTML:'unchanged'};
const ctx={console,setTimeout,clearTimeout,
 window:{addEventListener(){}},
 document:{querySelector(selector){if(selector==='#app')return app;if(selector==='#overlay-root')return overlay;return {}}}};
vm.createContext(ctx);
vm.runInContext(js.slice(0,js.lastIndexOf('(async function init(){')),ctx);
vm.runInContext('syncFloatingAssistant=()=>{};icon=()=>"<svg></svg>";renderLogin()',ctx);
const output=app.innerHTML;
assert.equal(overlay.innerHTML,'');
assert.equal((output.match(/<form\b/g)||[]).length,1);
assert.equal((output.match(/<input\b/g)||[]).length,2);
assert.equal((output.match(/<button\b/g)||[]).length,1);
assert(output.includes('class="login-page login-rebalanced"'));
assert(output.includes('class="login-stage"'));
assert(output.includes('class="login-visual" aria-hidden="true"'));
assert(output.includes('class="login-form-brand"'));
assert(output.includes('<strong>Framatex</strong>'));
assert(output.includes('<h1 id="login-title">Connexion</h1>'));
assert(output.includes('<main class="login-stage">'));
assert(output.includes('id="login-error"'));
assert(output.includes('for="email"')&&output.includes('for="password"'));
assert(output.includes('autocomplete="username"')&&output.includes('autocomplete="current-password"'));
assert(output.includes('type="submit">Se connecter</button>'));
assert.equal(form.submitType,'submit');
for(const removed of ['login-art','login-hero','login-caption','UNE NOUVELLE MANIÈRE','Chaque lancement','Bienvenue','Connectez-vous','ACCÈS SÉCURISÉ','prototype','administrateur','Dossier jaune numérique','Gestion documentaire']){
 assert(!output.includes(removed),'Redundant login text remains: '+removed);
}
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);
console.log('Framatex 0.26: balanced visual login, no promotional text, semantic form, mobile illustration hidden.');

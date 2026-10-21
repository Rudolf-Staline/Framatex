'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const main=fs.readFileSync('static/app.js','utf8');
const orders=fs.readFileSync('static/order-identification.js','utf8');
const css=fs.readFileSync('static/atelier.css','utf8');
const html=fs.readFileSync('static/index.html','utf8');
const mark=fs.readFileSync('static/jauno-mark.svg','utf8');

for(const source of [main,orders,fs.readFileSync('static/clients.js','utf8'),
 fs.readFileSync('static/floating-assistant.js','utf8')]){
 new vm.Script(source);
}
assert(html.includes('<title>JAUNO · Dossiers Jaunes</title>'));
assert(html.includes('/assets/jauno-mark.svg'));
assert(mark.includes('viewBox="0 0 64 64"'));
assert(main.includes("['launches','folder','Dossiers Jaunes']"));
assert(orders.includes('>Dossiers Jaunes<span class="heading-count">'));
assert(!orders.includes('>Commandes<span class="heading-count">'));
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);

for(const color of ['jaune','rose','bleu','vert']){
 assert(css.includes('.app-shell .main .folder-tab.folder-'+color));
 assert(css.includes('--tile-bg:') && css.includes('--tile-active:'));
}
assert(css.includes('.folder-tabs .folder-tab[class*="folder-"].selected'));
const a=main.indexOf('function renderSpaceChoice(){');
const b=main.indexOf('function renderLogin(',a);
assert(a!==-1 && b>a);
const renderChoice=main.slice(a,b);
const login=main.slice(b,main.indexOf('function tableLaunches(',b));
const authVisual=/<div class="login-visual" aria-hidden="true">.*?<\/div><\/div>/s;
assert.match(renderChoice,authVisual);
assert.match(login,authVisual);
assert(renderChoice.includes('login-page login-rebalanced jauno-space-choice'));
assert(login.includes('login-page login-rebalanced'));
assert(renderChoice.includes('login-stage'));
assert(renderChoice.includes('data-space="internal"'));
assert(renderChoice.includes('data-space="client"'));
assert(renderChoice.includes('JAUNO'));
assert(login.includes('JAUNO'));
assert(login.includes('Adresse e-mail') && login.includes('Mot de passe'));

const app={innerHTML:'',inert:false,querySelectorAll(){return []}};
const context={
 app,overlay:{innerHTML:''},state:{authSpace:'client'},resetModalState(){},
 syncFloatingAssistant(){},document:{body:{classList:{remove(){}}}},icon:()=>'<svg></svg>'
};
vm.createContext(context);
vm.runInContext(renderChoice+'renderSpaceChoice();',context);
assert.equal(context.state.authSpace,null);
assert(app.innerHTML.includes('Choisissez votre espace'));
assert(app.innerHTML.includes('Espace interne'));
assert(app.innerHTML.includes('Espace client'));
assert(!app.innerHTML.includes('id="email"'));
assert(!app.innerHTML.includes('id="password"'));
console.log('JAUNO: identity, login-matched space choice, persistent folder colors and labels OK');

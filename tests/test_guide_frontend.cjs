'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const guide=fs.readFileSync('static/guide.js','utf8');
assert(guide.includes("'/api/guide/actions/'"));
assert(guide.includes('textContent=text'));
assert(!guide.includes('innerHTML='));
assert(!guide.includes('eval('));
assert(guide.includes('requires_selection'));
assert(guide.includes("save('missing')"));
assert(guide.includes("save('finished')"));
assert(guide.includes('profile_key'));
assert(guide.includes('window.driver.js.driver'));
const checksum=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
assert.equal(checksum('static/vendor/driver.js'),checksum('node_modules/driver.js/dist/driver.js.iife.js'));
assert.equal(checksum('static/vendor/driver.css'),checksum('node_modules/driver.js/dist/driver.css'));
for(const page of ['static/index.html','static/partners.html','static/document-search.html','static/guide.html']){
 const html=fs.readFileSync(page,'utf8');assert(html.includes('/assets/guide.js'));assert(html.includes('/assets/vendor/driver.js'));assert(!html.includes('https://cdn'));
}
console.log('Framatex Guide : assets locaux, résolution fermée, rendu texte et identité de progression vérifiés');

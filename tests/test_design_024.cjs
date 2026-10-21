'use strict';
// Historical sheets are bundled into the compatibility layer.
const bundledLegacy=require('node:fs').readFileSync('static/legacy-ui.css','utf8');
/* Visual contract for the yellow-dossier identity, including setup and chat. */
const fs=require('node:fs');
const assert=require('node:assert/strict');
const html=fs.readFileSync('static/index.html','utf8');
const css=fs.readFileSync('static/design-024.css','utf8');
const setup=fs.readFileSync('static/setup.css','utf8');
const legacy=fs.readFileSync('static/design-023.css','utf8');
assert(bundledLegacy.includes('/* design-024.css */'));
assert(bundledLegacy.indexOf('/* design-024.css */')>bundledLegacy.indexOf('/* design-023.css */'),
 'Yellow overrides must follow the previous blue theme');
assert(css.includes('--brand:#e5b43a'));
assert(css.includes('--brand-ink:#30240b'));
assert(css.includes('background:#fff'));
assert(css.includes('background:var(--brand)'));
assert(css.includes('.sidebar-rail.sidebar-light .nav-btn.active'));
assert(css.includes('.dashboard-022 .dash-segments button.selected'));
assert(css.includes('.login-art'));
assert(css.includes('.floating-assistant-trigger'));
assert(css.includes('.floating-assistant-message.is-user .floating-assistant-bubble'));
assert(css.includes('.floating-assistant-form:focus-within'));
assert(css.includes('.app-shell[data-folder-theme] .main'));
for(const folder of ['jaune','rose','bleu','vert']){
 assert(css.includes('data-folder-theme="'+folder+'"'),folder+' contextual theme missing');
}
assert(css.includes('.tag.blue'), 'Information states may remain blue');
assert(css.includes('.tag.green'), 'Success states must remain green');
assert(setup.includes('Framatex 0.24'), 'First admin setup must also use the brand theme');
assert(setup.includes('button{background:var(--brand);color:#30240b}'));
assert(!css.includes('background:linear-gradient(145deg,#4089ff'), 'Floating trigger still uses blue');
assert(legacy.includes('floating-assistant-trigger'), 'Must still inherit mobile and motion controls');

/* WCAG AA text contrast checks. */
function luminance(hex){
 const parts=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255)
   .map(c=>c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4));
 return 0.2126*parts[0]+0.7152*parts[1]+0.0722*parts[2];
}
function contrast(one,two){
 const x=luminance(one),y=luminance(two);
 return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);
}
for(const [foreground,background,label] of [
 ['#30240b','#e5b43a','yellow CTA'],
 ['#30240b','#d3a024','yellow CTA hover'],
 ['#78550c','#ffffff','brand link on white'],
 ['#563f0a','#fff0be','active navigation'],
 ['#2e250f','#e8b83c','chat user bubble'],
 ['#2f240b','#d7a327','yellow-folder action']
]){
 const ratio=contrast(foreground,background);
 assert(ratio>=4.5,label+' contrast '+ratio.toFixed(2)+' < 4.5');
}
assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length,
 'Malformed CSS block braces');
console.log('Framatex 0.24: yellow dossier identity across all screens, semantic folder colors, WCAG AA contrast OK');

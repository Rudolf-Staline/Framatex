'use strict';
document.getElementById('search-form').dataset.guideTarget='document-search';
FramatexGuide.register({surface:()=> 'internal',context:()=>({page:'search'}),welcomeHost:()=>null,go:async d=>d.id==='search'});

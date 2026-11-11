'use strict';
let offset=0;
const $=id=>document.getElementById(id);
function node(tag,text){const n=document.createElement(tag);n.textContent=text;return n;}
async function search(){
 const data=new URLSearchParams();for(const [key,value] of new FormData($('search-form')))if(value)data.set(key,['after','before'].includes(key)?new Date(value).toISOString():value);
 data.set('offset',String(offset));data.set('limit','25');$('search-status').textContent='Recherche en cours…';
 try{const r=await fetch('/api/document-search?'+data);const result=await r.json();if(!r.ok)throw new Error(typeof result.detail==='string'?result.detail:'Filtres invalides');
 $('search-results').replaceChildren();$('search-status').textContent=`${result.total} version(s) autorisée(s) · Page ${Math.floor(offset/25)+1}`;
 for(const doc of result.items){const a=node('article','');a.append(node('h2',doc.title),node('p',`${doc.doc_type} · ${doc.folder} · ${doc.order_ref||'Commande non renseignée'} · version ${doc.version}`));const link=node('a','Télécharger');link.href=doc.download_url;a.append(link);$('search-results').append(a);}
 $('previous').disabled=offset===0;$('next').disabled=offset+25>=result.total;
 }catch(error){$('search-status').textContent=error.message;$('search-results').replaceChildren();}
}
$('search-form').onsubmit=event=>{event.preventDefault();offset=0;search();};
$('previous').onclick=()=>{offset=Math.max(0,offset-25);search();};$('next').onclick=()=>{offset+=25;search();};
search();

'use strict';
let offset=0, requestNumber=0;
const $=id=>document.getElementById(id);
function node(tag,text){const element=document.createElement(tag);element.textContent=text;return element;}

function resultCard(doc){
 const card=node('article','');
 const headline=node('div','');
 headline.append(node('h3',doc.title));
 const metadata=node('p','');
 const folder=node('span',doc.folder);
 folder.className='search-folder';
 if(['jaune','rose','bleu','vert'].includes(doc.folder))folder.dataset.folder=doc.folder;
 metadata.append(folder,document.createTextNode(` ${doc.doc_type} · ${doc.order_ref||'Commande non renseignée'} · v${doc.version}`));
 headline.append(metadata);
 const link=node('a','Télécharger');
 link.href=doc.download_url;
 card.append(headline,link);
 return card;
}
async function search(){
 const request=++requestNumber, pageOffset=offset;
 const results=$('search-results');
 const status=$('search-status');
 const previous=$('previous'),next=$('next');
 results.setAttribute('aria-busy','true');
 previous.disabled=next.disabled=true;
 status.textContent='Recherche en cours…';
 try{
  const data=new URLSearchParams();
  for(const [key,value] of new FormData($('search-form')))if(value)data.set(key,['after','before'].includes(key)?new Date(value).toISOString():value);
  data.set('offset',String(pageOffset));
  data.set('limit','25');
  const response=await fetch('/api/document-search?'+data);
  const result=await response.json();
  if(request!==requestNumber)return;
  if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Filtres invalides');
  status.textContent=`${result.total} ${result.total>1?'versions accessibles':'version accessible'} · Page ${Math.floor(pageOffset/25)+1}`;
  results.replaceChildren(...result.items.map(resultCard));
  if(!result.items.length){
   const empty=node('p','Aucun document ne correspond à ces critères.');
   empty.className='search-empty';
   results.append(empty);
  }
  previous.disabled=pageOffset===0;
  next.disabled=pageOffset+25>=result.total;
 }catch(error){
  if(request!==requestNumber)return;
  status.textContent=error instanceof TypeError?'Connexion interrompue. Relancez votre recherche.':error.message;
  results.replaceChildren();
 }finally{
  if(request===requestNumber)results.removeAttribute('aria-busy');
 }
}
$('search-form').onsubmit=event=>{event.preventDefault();offset=0;search();};
$('previous').onclick=()=>{offset=Math.max(0,offset-25);search();};
$('next').onclick=()=>{offset+=25;search();};
search();

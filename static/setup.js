"use strict";
const form=document.getElementById("setup-form");
const status=document.getElementById("status");
form.addEventListener("submit",async event=>{
  event.preventDefault();
  status.textContent="";status.className="";
  const password=document.getElementById("password").value;
  if(password!==document.getElementById("password-confirm").value){status.className="error";status.textContent="Les mots de passe ne correspondent pas.";return;}
  const button=document.getElementById("submit");button.disabled=true;
  try{
    const response=await fetch("/api/setup/first-admin",{
      method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","X-Framatex-Request":"1"},
      body:JSON.stringify({token:document.getElementById("token").value,email:document.getElementById("email").value,name:document.getElementById("name").value,password})
    });
    const data=await response.json();
    if(!response.ok) throw new Error(typeof data.detail==="string"?data.detail:"Initialisation impossible");
    form.reset();status.className="ok";status.textContent="Compte créé. Tu peux maintenant te connecter sur la page principale.";
    const link=document.createElement("a");link.href="/";link.textContent="Ouvrir Framatex →";link.style.display="block";link.style.marginTop="12px";status.appendChild(link);
  }catch(error){status.className="error";status.textContent=error.message||"Erreur de connexion"}
  finally{button.disabled=false;}
});

'use strict';
const form = document.querySelector('#setup-form');
const status = document.querySelector('#status');
const value = id => document.getElementById(id).value;
form.addEventListener('submit', async event => {
  event.preventDefault();
  status.textContent = '';
  if (value('password') !== value('confirm')) {
    status.textContent = 'Les deux mots de passe ne correspondent pas.';
    return;
  }
  const button = form.querySelector('button');
  button.disabled = true;
  try {
    const response = await fetch('/api/setup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Framatex-Request': '1',
                'X-Framatex-Setup-Token': value('secret')},
      body: JSON.stringify({name: value('name'), email: value('email'), password: value('password')}),
      cache: 'no-store',
      credentials: 'same-origin'
    });
    if (response.status === 201) {
      form.reset();
      window.location.replace('/espace-framatex');
      return;
    }
    status.textContent = response.status === 404
      ? 'Installation indisponible ou secret incorrect.'
      : 'Installation non effectuée. Vérifiez les informations.';
  } catch {
    status.textContent = 'Connexion interrompue. Vérifiez si l’installation a abouti.';
  } finally {
    button.disabled = false;
  }
});

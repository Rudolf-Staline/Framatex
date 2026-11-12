# Rapport de sécurité phase 3

## Mesures implémentées

- Dossier canonique unique par commande ; contrôle de tous les lancements historiques restreints avant accès. Aucune permission n'est déduite d'un client de même nom ou d'une référence approchante.
- Contrôles sur les routes commande, document, version, passeport, circuit, téléchargement, recherche, annuaire métier, réception et notification. Filtrage avant comptage/pagination. Les comptes externes restent limités à leurs demandes et publications explicites.
- Fichiers privés écrits en création exclusive, mode 0600, nom opaque, maximum 20 Mio. Chemins et noms invalides refusés. Budget privé total configurable (1 Gio par défaut), verrou non bloquant partagé entre workers, refus 409 des dépôts concurrents et refus 413 du dépassement de quota. Les aperçus passent par le même stockage et les mêmes contrôles, puis sont supprimés. Suppression des nouveaux blobs si validation, scanner ou transaction échoue. Les fichiers historiques ne sont pas modifiés.
- Vérification de structure en sous-processus : mémoire 512 Mio, CPU 8 s, délai 12 s ; archives Office bornées, chemins internes/entrées dupliquées/chiffrement ZIP/macros/objets incorporés/liens externes Excel/entités XML/DDE refusés ; images vérifiées et plafonnées à 12 Mpx ; actions PDF automatiques refusées. Ces contrôles ne constituent pas une preuve d'absence de malware.
- Extraction isolée : mémoire 768 Mio, CPU 25 s, délai 35 s, limite PDF 3 pages, texte 16 000 caractères, XLSX 3 feuilles × 120 lignes × 16 colonnes. Les limites et la provenance accompagnent le résultat ; les valeurs restent à confirmer. Les documents protégés, corrompus et l'OCR indisponible sont signalés. Aucun document réel fourni.
- ORLI : maximum 3 Mio, 1 000 lignes ; vérification/lecture dans un processus mémoire 512 Mio, CPU 8 s, délai 12 s ; analyse antivirus selon politique avant import. Références absentes, ambiguïtés et valeurs incompatibles empêchent une association silencieuse. Résolution explicite, motif, empreinte du snapshot et audit. Le réimport ne modifie jamais automatiquement un lien antérieur.
- Réouverture : nouvelle ligne de circuit, séquence/version exactes, ancien circuit et décisions conservés, écriture sérialisée, contraintes uniques, statut de publication révoqué, notifications et contrôle de la dernière séquence. Aucune validation historique n'est effacée.

## Antivirus réel

Configurer explicitement :

```
FRAMATEX_UPLOAD_SCAN_MODE=required
FRAMATEX_SCANNER_BACKEND=clamav
FRAMATEX_SCANNER_COMMAND=clamscan --no-summary --alert-encrypted=yes
FRAMATEX_SCANNER_TIMEOUT_SECONDS=30
```

Le scanner s'exécute avant disponibilité. Retour 1 → refus 422 ; scanner absent, erreur, délai ou base absente → refus 503. Aucun basculement automatique en mode désactivé. `disabled` signifie explicitement **aucune analyse antivirus**. La configuration d'exemple reste une démonstration, à changer avant exploitation. Les journaux d'analyse ne contiennent ni chemin, nom, contenu ni donnée de compte.

ClamAV 1.4.3 a été exécuté localement sans élévation : paquets Debian extraits dans `/tmp/framat-clamav`, bibliothèques locales. Test EICAR non malveillant et base de signatures synthétique limitée à EICAR ; le même test réel est installé dans GitHub Actions via le paquet ClamAV. Le test est explicitement ignoré si l'exécutable n'existe pas : ne pas utiliser un succès global avec ce test ignoré comme preuve antivirus.

Chaque analyse relance un processus : un redémarrage ne réutilise pas un ancien résultat « sain ». La base de signatures, ses mises à jour, ses permissions et son approvisionnement restent une responsabilité d'exploitation. **Les signatures antivirus complètes et leur mise à jour n'ont pas été vérifiées dans cet environnement** : N-09 reste partiel par prudence, malgré la preuve du moteur réel et de l'adaptateur.

## Limites de la vérification

Corpus synthétique et contrôles ciblés : pas d'audit de pénétration exhaustif, pas de conformité WCAG complète revendiquée, pas de validation de données de production. Les bibliothèques de parsing doivent être maintenues à jour. Les règles réglementaires et métiers de chaque rubrique doivent être confirmées par Framatex. Les dépendances ORLI direct, email réel et autres exigences externes ne sont pas simulées comme terminées.

Blocage réseau observé : `curl -I --max-time 20 https://database.clamav.net/daily.cvd` a échoué avec CONNECT 403. Le téléchargement Playwright depuis `cdn.playwright.dev` a également été refusé (403) ; Chromium local a permis les parcours réels, tandis que la CI installe explicitement le navigateur Playwright. Aucune politique réseau ni protection antivirus n’a été désactivée pour contourner ces refus.

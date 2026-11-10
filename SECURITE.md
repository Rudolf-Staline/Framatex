# Contrôles et limites de sécurité

- Sessions partenaires opaques de 8 h, stockées uniquement sous SHA256 ; invitations de 24 h à usage unique ; mots de passe Argon2 et minimum 12 caractères.
- Une invitation renouvelée invalide les anciennes invitations ; l'activation/récupération invalide toutes les sessions. La récupération est assistée par un administrateur après vérification d'identité hors application.
- Suspension d'une organisation ou d'un compte : refus immédiat et consommation des jetons. La réactivation ne restaure pas les sessions précédentes.
- Cookie HttpOnly/SameSite strict, Secure avec `FRAMATEX_SECURE_COOKIE=1`. En-tête obligatoire sur les écritures ; pas de CORS permissif ajouté. CSP sur `/partners`, données insérées dans le DOM avec textContent.
- Authentification partenaire distincte des employés. Chaque lecture, message, dépôt et téléchargement contrôle l'organisation côté serveur. Les autres objets renvoient 404. Les opérations administratives exigent un administrateur authentifié.
- Publication client : attribution explicite, type autorisé, version approuvée et courante, destinataire cohérent, retrait vérifié à chaque accès. Aucun accès direct aux dossiers internes.
- Fichiers limités à 20 Mo, extensions autorisées et validation structurelle réutilisée. Noms physiques aléatoires, fichiers privés hors static, téléchargement en pièce jointe. Une validation structurelle n'est pas un antivirus.
- Audit interne et historique partenaire conservés. Pas d'immutabilité juridique revendiquée. Erreurs SMTP enregistrées par classe seulement, sans réponses serveur ni secrets.
- Invitations renvoyées une seule fois à l'administrateur, jamais journalisées ; transmission manuelle par canal autorisé, pas de faux message « email envoyé ».

## Conditions avant pilote externe

Revue indépendante des droits, tests de charge/concurrence, protection réseau contre abus, quotas de stockage, scan malware, HTTPS, sauvegarde protégée et validation métier sont encore nécessaires. Le limiteur de connexion est local au processus ; prévoir un stockage partagé et une limitation au proxy avant multi-worker. Le parcours ne gère pas encore tous les rôles fournisseurs, domaines emails autorisés, MFA, pièces jointes de messages, délégations ni politiques de rétention. Ne pas ouvrir ce travail comme un portail de production.

Les archives de sauvegarde contiennent des données privées et des hachés de mots de passe : protéger leur accès, chiffrer leur stockage selon la politique Framatex. Restaurer depuis une archive locale de confiance, en maintenance. Aucune donnée réelle utilisée pendant cette mission.

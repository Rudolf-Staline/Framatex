# Administration des partenaires

1. Se connecter à l'application interne avec un compte administrateur, puis ouvrir `/partners` et « Administration ».
2. Créer l'organisation fournisseur ou client. Ajouter un contact par son email. Copier le code d'invitation affiché et le transmettre par un canal autorisé ; aucun email d'invitation n'est envoyé. Le code expire sous 24 h.
3. Créer une demande avec fournisseur, identifiant du lancement existant, référence commande, titre, type documentaire et échéance.
4. Ouvrir la demande, télécharger chaque version reçue, saisir le motif puis approuver ou demander une correction. Un dépôt n'est jamais approuvé automatiquement. Après approbation, clôturer.
5. Pour une réception, créer la ligne matière et la quantité commandée. Utiliser l'identifiant de version affiché dans la preuve de dépôt. Confirmer les quantités réellement réceptionnées avec un justificatif approuvé ; enregistrer séparément les retours. Les déclarations fournisseurs restent visibles séparément.
6. Pour un client, approuver puis publier une version via le partage interne existant ; attribuer son identifiant de publication au client dans `/partners`. Le nom légal doit correspondre au destinataire. Un retrait dans le partage interne coupe immédiatement le téléchargement externe ; un remplacement de version le rend également indisponible.
7. Révoquer un contact ou suspendre l'organisation depuis sa carte. Réactiver ne rétablit aucune ancienne session. Pour récupération après contrôle d'identité, renouveler l'invitation.

Les formulaires demandent actuellement des identifiants de lancement/publication/pièce : amélioration UX restante. Les pièces fournisseurs ne sont pas automatiquement versées aux dossiers internes. Les demandes historiques « simulées » sont distinctes, sans migration automatique. La liste des demandes affiche les 100 plus récentes ; pagination API disponible par `offset` et `limit`.

File email : visible dans `/partners`, préférences gérées par chaque contact. Le transport est désactivé tant qu'il n'est pas configuré et autorisé. Un état `accepted` signifie uniquement accepté par SMTP ; `processing` après incident nécessite une vérification avant remise en file. Après cinq tentatives en échec, traitement manuel requis.

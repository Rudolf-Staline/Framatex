# Guide fournisseur

Ouvrir `/partners`, dérouler « Activer ou récupérer mon compte », saisir le code reçu de Framatex et choisir un mot de passe de 12 caractères minimum. Se connecter ensuite avec son email.

La liste affiche seulement les demandes de votre organisation. Ouvrir une demande, vérifier la commande et transmettre le document attendu. La preuve de dépôt affiche numéro, date, identifiant et SHA256. Le statut initial est « Vérification en attente ». Un refus montre sa justification et permet un nouveau dépôt : la précédente version reste consultable. Après approbation puis clôture, aucun dépôt supplémentaire n'est possible.

Le fil conserve les messages et décisions. « Enregistrer le message » enregistre dans Framatex ; il ne signifie pas qu'un email a été envoyé. La préférence email peut être activée, mais un transport configuré par Framatex est nécessaire.

Les commandes matières affichent le commandé, le déclaré, le réceptionné net et le restant. Une déclaration doit citer la version du justificatif de la même commande et indiquer quantité, date et justification. Seul Framatex confirme une réception ou un retour. Une réception partielle n'est pas une erreur.

En cas de code expiré, de récupération ou de compte suspendu, contacter votre interlocuteur Framatex. Utiliser « Déconnexion partenaire » pour révoquer la session courante.

## Pièces reçues par Framatex hors portail

L'adoption du portail n'est pas obligatoire pour enregistrer une réception. Un collaborateur se connecte à l'espace interne, ouvre `/partners` puis « Espace Framatex ». Dans une demande ouverte ou refusée, il choisit « Pièce reçue hors portail », renseigne le canal (email, papier numérisé, remise directe ou autre), décrit la provenance et dépose le fichier. L'application conserve son identité de collaborateur ; aucun compte fournisseur n'est créé pour lui attribuer artificiellement ce dépôt.

La pièce passe en vérification. Un collaborateur habilité à l'examen approuve ou demande une correction avec motif ; une nouvelle transmission conserve l'ancienne. L'intégration au dossier demande les droits de lecture, dépôt et examen de la rubrique cible. Une intégration retirée reste dans l'historique mais ne satisfait plus les contrôles métier. Une demande clôturée doit être rouverte avant un nouveau dépôt ou échange.

## Habilitations internes et suivi

L'administration attribue explicitement les droits suivants ; la mise à niveau n'en accorde aucun automatiquement :

| Usage | Droit métier | Droits de contexte également requis |
|---|---|---|
| Consulter les demandes | `supplier.read` | Lecture du lancement/commande et de Jaune |
| Créer une demande, enregistrer une pièce reçue, rouvrir/clôturer | `supplier.request` | Lecture du contexte et de Jaune ; dépôt Jaune pour enregistrer un fichier |
| Décider d'une transmission | `supplier.review` | Lecture du contexte et de Jaune |
| Consulter les réceptions | `receipt.read` | Lecture du contexte, de Jaune et de Rose |
| Réceptionner, retourner ou annuler un mouvement | `receipt.write` | Lecture du contexte, de Jaune et de Rose |

Les usages de lecture s'attribuent en complément des droits d'action nécessaires. La création d'une ligne matière relève des demandes fournisseurs. L'administration des organisations, contacts, accès clients et rôles reste distincte.

La liste Réceptions est paginée ; son lien ouvre la rubrique Rose de la commande si elle existe, sinon le lancement réellement associé. Les listes n'incluent plus tout l'historique : dans l'espace partenaires, « Consulter et corriger les mouvements » et « Charger les situations suivantes » l'affichent à la demande. Les quantités restent décimales avec leur unité. Commandé, prévu, annoncé, déclaré, reçu, retourné et restant sont distincts ; une différence ou une échéance dépassée invite au rapprochement et ne définit pas à elle seule une règle officielle d'anomalie.

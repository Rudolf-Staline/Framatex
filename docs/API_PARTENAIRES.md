# API partenaires

Contrat exécutable complet : `/openapi.json`, interface `/docs`. Toutes les écritures exigent `X-Framatex-Request: 1`. Les API internes utilisent le cookie employé ; les externes le cookie HttpOnly `framat_partner`.

| Préfixe / route | Accès / fonction |
|---|---|
| `/api/partners/organizations` | administrateur : liste/création |
| `/api/partners/organizations/{id}` | administrateur : suspension/réactivation |
| `/api/partners/organizations/{id}/accounts` | administrateur : contacts |
| `/api/partners/organizations/{id}/invitations` | administrateur : code à usage unique / récupération |
| `/api/partners/accounts/{id}` | administrateur : révocation/réactivation |
| `/api/partner-auth/activate`, `login`, `logout` | activation, session et révocation |
| `/api/partner/home` | identité partenaire courante |
| `/api/partners/requests` | administrateur : création/liste paginée |
| `/api/partner/requests` | fournisseur : liste paginée isolée |
| `…/requests/{id}` | détail, historique et versions |
| `/api/partner/requests/{id}/versions` | dépôt multipart `file` |
| `…/requests/{id}/versions/{version}/download` | téléchargement contrôlé |
| `/api/partners/requests/{id}/decision` | version_id, decision approved/rejected, reason obligatoire |
| `/api/partners/requests/{id}/close` | clôture après approbation |
| `…/requests/{id}/messages` | message textuel persistant |
| `/api/partners/publications` | attribuer publication_id à partner_id client |
| `/api/partner/publications` | publications effectives pour le client courant |
| `/api/partner/publications/{id}/download` | version publiée revalidée |
| `/api/partners/order-lines` | administrateur : création/liste |
| `/api/partner/order-lines` | fournisseur : liste isolée |
| `/api/partner/order-lines/{id}/declarations` | quantité déclarée, source_id, date, note, operation_key |
| `/api/partners/order-lines/{id}/receipts` | confirmation received/returned par administrateur |
| `/api/partner/mail-preference` | lecture/modification de préférence |
| `/api/partners/mail` | file et erreurs pour administrateur |

Dates au format ISO, quantités décimales à trois décimales. Pagination des demandes : offset ≥ 0, limit de 1 à 100. Les écritures incompatibles renvoient 409 ; validation 422 ; absence de session 401 ; ressource d'une autre organisation 404. Les mouvements exigent une clé idempotente stable lors d'une reprise ; réutiliser la même clé avec un contenu différent renvoie 409.

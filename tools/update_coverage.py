"""Render the fixed 273 requirements; statuses must be reviewed against executed tests."""
import json
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=json.loads((root/'docs/requirements.json').read_text())
assert len(rows)==273 and len({r['id'] for r in rows})==273
counts=Counter(r['status'] for r in rows)
lines=['# Couverture fonctionnelle', '', f"**{counts['terminé']} / 273 exigences terminées : {counts['terminé']/273*100:.1f} %. Objectif 90 % {'atteint en environnement contrôlé' if counts['terminé'] >= 246 else 'non atteint'}.**",'',f'États : {dict(counts)}. Périmètre fixe conservé depuis la phase 1. Aucun blocage exclu du dénominateur. Terminé signifie testé en environnement contrôlé, jamais validé pour production par Framatex. Voir IMPLEMENTATION_STATUS.md pour les commandes exécutées et limites.','', '| ID | Priorité | Exigence | État | Implémentation | Test | Résultat / dépendance |','|---|---|---|---|---|---|---|']
for r in rows:lines.append('| '+' | '.join(str(r[k]).replace('|','/') for k in ('id','priority','requirement','status','files','test'))+' | '+r['observed']+' ; '+r['dependency']+' |')
(root/'COUVERTURE_FONCTIONNELLE.md').write_text('\n'.join(lines)+'\n')
print(counts)

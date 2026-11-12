"""Generate the offline French manual from exactly the shipped procedure catalogue."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def render():
    data=json.loads((ROOT/'app/guide_data/catalog.fr.json').read_text())
    profiles={'admin':'administrateur','employee':'employé','supplier':'fournisseur','client':'client','public':'visiteur'}
    lines=['# Manuel utilisateur Framatex','',f"Catalogue {data['version']} · français · une commande = un Dossier Jaune unique.",'','Ouvrez **Framatex Guide** depuis tout espace pour rechercher une procédure, consulter l’aide contextuelle ou démarrer une visite. La visite ne confirme aucune opération métier. Les fonctions présentées dépendent de votre profil et de vos permissions. Le centre d’aide et les visites fonctionnent sans Gemini.','', 'Première connexion : **Commencer la visite** démarre une présentation adaptée à vos droits ; **Plus tard** reporte la proposition à une connexion ultérieure ; **Ne plus proposer automatiquement** conserve ce choix. Le bouton **Mes visites** permet ensuite de reprendre une visite ou de la recommencer ou de l’ignorer. Aucun bouton de validation métier n’est confirmé par la visite.','', 'Le centre d’aide propose des catégories, des procédures populaires, les consultations récentes et l’aide de la page actuelle. **Centre d’aide en pleine page** ouvre la page permanente. Les questions de suivi peuvent se référer à la dernière procédure sélectionnée, sans conserver le texte de la conversation. À la fin d’une procédure, **Oui** ou **Non** enregistre un retour minimal ; un signalement catégorisé évite de stocker des données confidentielles.','', 'Les procédures fournisseur et client s’appliquent aux commandes et demandes expressément autorisées. Les règles métier des rubriques, l’extraction sur corpus réel et les signatures antivirus complètes gardent les limites indiquées dans les rapports du projet.','']
    for p in data['procedures']:
        lines += [f"## {p['title']}",'',f"Identifiant permanent : `{p['id']}` · profils : {', '.join(profiles[a] for a in p['audience'])} · catégorie : {p['category']}",'',p['description'],'','Prérequis : '+ ' ; '.join(p['prerequisites'])+'.','']
        lines += [f"{i+1}. {s['description']}" for i,s in enumerate(p['steps'])]
        lines += ['', 'Résultat : '+p['result'],'','Problèmes fréquents :']
        lines += [f"- {item['problem']} : {item['solution']}" for item in p['problems']]
        lines += ['',f"Raccourci : destination enregistrée `{p['destination']}`. Visite : `{p['tour_id']}`."]
        if p['limitations']:lines+=['','Limites : '+' ; '.join(p['limitations'])]
        lines+=['']
    return '\n'.join(lines).rstrip()+'\n'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args();target=ROOT/'GUIDE_UTILISATEUR_FRAMATEX.md';content=render()
    if args.check:assert target.is_file() and target.read_text()==content,'Manuel désynchronisé : exécuter tools/build_guide_manual.py'
    else:target.write_text(content)
    print('Manuel synchronisé')

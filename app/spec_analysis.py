"""Suggestions explicables à partir de texte borné, sans IA et sans validation automatique.

L'analyse est volontairement limitée aux 3 premières pages / 16 000 caractères
par le lecteur documentaire partagé. Aucun passage non détecté n'est réputé conforme.
"""
from __future__ import annotations
import re
import unicodedata

MAX_LINES = 100
MAX_PROPOSALS = 30

DEMAND = re.compile(r'\b(doit|doivent|devra|devront|exig[eé]s?|obligatoire|tol[eé]rance|composition|mati[eè]re|couleur|dimensions?|boutons?|fermeture|conditionnement|shall|required|must|tolerance|fabric|color|colour|buttons?)\b', re.I)
RULES = [
 ('intensite_imprecise', re.compile(r'\b(l[eé]g[eè]rement|assez|plus ou moins|environ|approximativement|suffisamment|aussi proche que possible|roughly|approximately|slightly)\b',re.I), 'Quelle valeur mesurable et quelle tolérance faut-il retenir ?'),
 ('reference_absente', re.compile(r'\b(mod[eè]le pr[eé]c[eé]dent|comme d.habitude|[eé]quivalent|similaire|same as previous|as usual|equivalent)\b',re.I), 'Quelle référence précise ou quelle version de référence doit être utilisée ?'),
 ('decision_en_suspens', re.compile(r'\b([aà] confirmer|reste [aà] d[eé]finir|selon disponibilit[eé]|[aà] valider|[tT][bB][cC]|to be confirmed|TBD|pending confirmation)\b',re.I), 'Qui doit confirmer cette information et dans quel délai ?'),
 ('urgence_non_datee', re.compile(r'\b(d[eè]s que possible|au plus vite|urgent|asap)\b',re.I), 'Quelle échéance calendaire ou opérationnelle s’applique ?'),
]

def _normalize(s:str)->str:
    return ''.join(c for c in unicodedata.normalize('NFD',s.casefold()) if unicodedata.category(c) != 'Mn')

def _lines(text:str):
    # Une spécification peut être organisée en puces ou en phrases longues.
    for raw in text.splitlines()[:MAX_LINES]:
        value=' '.join(raw.split())
        if len(value)>=9:
            yield value[:500]

def analyze_text(text: str)->dict:
    req=[]; ambiguities=[]; seen_req=set(); seen_amb=set()
    for line in _lines(text[:16000]):
        normalized=_normalize(line)
        if DEMAND.search(line) and normalized not in seen_req and len(req)<MAX_PROPOSALS:
            category='Autre'
            if re.search('tissu|mati[eè]re|fabric|composition',line,re.I):category='Matière'
            elif re.search('taille|dimension|longueur|largeur|tol[eé]rance|tolerance',line,re.I):category='Dimensions'
            elif re.search('bouton|fermeture|zip|accessoire',line,re.I):category='Accessoires'
            elif re.search('couleur|color|colour',line,re.I):category='Couleur'
            elif re.search('emballage|conditionnement|packaging',line,re.I):category='Conditionnement'
            req.append({'title':line[:120], 'category':category, 'description':line, 'source_excerpt':line,
                        'reason':'Terme potentiellement prescriptif détecté, à confirmer par un professionnel'})
            seen_req.add(normalized)
        for kind,regex,question in RULES:
            if regex.search(line) and (kind,normalized) not in seen_amb and len(ambiguities)<MAX_PROPOSALS:
                ambiguities.append({'kind':kind, 'excerpt':line, 'question':question,
                                    'reason':'Expression nécessitant potentiellement une clarification'})
                seen_amb.add((kind,normalized))
    return {'requirements':req, 'ambiguities':ambiguities,
            'limits':'Suggestions lexicales uniquement, sur le texte accessible et tronqué ; absence de résultat ≠ conformité. Validation humaine obligatoire.'}

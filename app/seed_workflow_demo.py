"""Génère uniquement des exemples fictifs du workflow 0.3 ; peut être relancé."""
from sqlalchemy import select
from .core import Base, SessionLocal, engine
from .main import STORAGE
from .models import User, Launch, Document
from .workflow import emit_impacts
from .workflow_models import BusinessValueRevision, DocumentReview, ImpactRule, ImpactAlert


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email.is_not(None)))
        if not user:
            raise SystemExit('Créer l’administrateur avant de générer les données de démonstration.')
        launch=db.scalar(select(Launch).where(Launch.name == 'Chemises manches longues · pilote B'))
        if not launch:
            raise SystemExit('Exécutez auparavant : python -m app.seed_demo')
        source=db.scalar(select(Document).where(Document.folder_id.in_([f.id for f in launch.folders if f.slug=='jaune'])))
        if not source or len(source.versions)<2:
            raise SystemExit('Le scénario fictif nécessite la fiche d’emploi v1 et v2 du jeu de démonstration.')
        rule_name='Consommation tissu → révision des besoins'
        rule=db.scalar(select(ImpactRule).where(ImpactRule.name==rule_name))
        if not rule:
            rule=ImpactRule(name=rule_name,source_kind='value',source_key='consommation_matiere',
                source_folder='jaune',target_folder='jaune',
                instruction='Vérifier les besoins matière et les fiches de prix à la suite du changement de consommation.',
                created_by=user.id)
            db.add(rule)
        other_name='Fiche d’emploi révisée → réception'
        other=db.scalar(select(ImpactRule).where(ImpactRule.name==other_name))
        if not other:
            other=ImpactRule(name=other_name,source_kind='document',source_key='Fiche d’emploi',
                source_folder='jaune',target_folder='rose',
                instruction='Vérifier si la réception doit prendre connaissance de la nouvelle fiche d’emploi.',
                created_by=user.id)
            db.add(other)
        db.flush()
        r1=db.scalar(select(BusinessValueRevision).where(BusinessValueRevision.launch_id==launch.id,
                                                           BusinessValueRevision.key=='consommation_matiere',
                                                           BusinessValueRevision.revision==1))
        v1,v2=sorted(source.versions,key=lambda v:v.number)[:2]
        if not r1:
            db.add(BusinessValueRevision(launch_id=launch.id,key='consommation_matiere',revision=1,
                value_text='1.8',unit='m/pièce',source_version_id=v1.id,
                reason='Consommation indiquée dans la version initiale (données fictives)',recorded_by=user.id))
            db.flush()
        r2=db.scalar(select(BusinessValueRevision).where(BusinessValueRevision.launch_id==launch.id,
                                                           BusinessValueRevision.key=='consommation_matiere',
                                                           BusinessValueRevision.revision==2))
        if not r2:
            r2=BusinessValueRevision(launch_id=launch.id,key='consommation_matiere',revision=2,
                value_text='1.9',unit='m/pièce',source_version_id=v2.id,
                reason='Consommation révisée dans la nouvelle fiche d’emploi (données fictives)',recorded_by=user.id)
            db.add(r2);db.flush()
        if not db.scalar(select(ImpactAlert).where(ImpactAlert.rule_id==rule.id,ImpactAlert.source_ref_id==r2.id)):
            emit_impacts(db,launch_id=launch.id,source_kind='value',source_key='consommation_matiere',
                source_folder='jaune',source_ref_id=r2.id,old_value='1.8 m/pièce',new_value='1.9 m/pièce')
        if not db.scalar(select(ImpactAlert).where(ImpactAlert.rule_id==other.id,ImpactAlert.source_ref_id==v2.id)):
            emit_impacts(db,launch_id=launch.id,source_kind='document',source_key='Fiche d’emploi',
                source_folder='jaune',source_ref_id=v2.id,new_value='v2')
        if not db.scalar(select(DocumentReview).where(DocumentReview.document_version_id==v1.id)):
            db.add(DocumentReview(document_version_id=v1.id,decision='approved',
                comment='Version initiale vérifiée (validation fictive)',reviewed_by=user.id))
        db.commit()
        print('Workflow 0.3 fictif prêt : 2 règles, 2 valeurs sourcées, alertes de dépendance et validation v1.')
        print('Ouvrez le lancement « Chemises manches longues · pilote B » dans l’application.')

if __name__=='__main__':
    main()

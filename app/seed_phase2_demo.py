"""Reproducible isolated demonstration, with explicit DEMO mode and supplied password."""
import os,json
from datetime import date,timedelta
from decimal import Decimal
from sqlalchemy import select
from .demo_guard import require_demo


def main():
    require_demo()
    password=os.getenv('FRAMATEX_DEMO_PASSWORD','')
    if not os.getenv('FRAMATEX_DATA_DIR') or not 12<=len(password)<=256:
        raise SystemExit('Dossier FRAMATEX_DATA_DIR dédié et FRAMATEX_DEMO_PASSWORD (12–256 caractères) requis.')
    from .main import app,STORAGE
    from .core import SessionLocal,hash_password
    from .migrate import migrate
    from .models import User,Role,Launch,AuditEvent
    from .partner_models import Partner,PartnerAccount,PartnerRequest,PartnerSubmission,PartnerEvent,PartnerOrderLine,PartnerDelivery,PartnerPublication
    from .partner_phase2_models import PartnerRole,PartnerRoleAssignment,PartnerClientOrder,PartnerClientOrderEvent,BusinessOrder,BusinessOrderLaunch,PartnerIntegration
    from .workflow_models import DocumentReview
    from .sharing_models import ClientPublication
    from .seed_quality_demo import add_doc
    from .partner_notice_routes import emit,generate_due
    migrate()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email!='demo-admin@example.local')):
            raise SystemExit('Installation non dédiée : comptes internes existants, démonstration refusée.')
        admin=db.scalar(select(User).where(User.email=='demo-admin@example.local'))
        if not admin:
            admin=User(name='Administrateur DÉMO',email='demo-admin@example.local',password_hash=hash_password(password),roles=[Role(name='Administrateur')]);db.add(admin);db.commit()
    # Keep the original seed entrypoints; do not duplicate their fixtures.
    from . import seed_demo,seed_completeness_demo,seed_workflow_demo,seed_quality_demo
    for module in (seed_demo,seed_completeness_demo,seed_workflow_demo,seed_quality_demo):module.main()
    with SessionLocal() as db:
        admin=db.scalar(select(User).where(User.email=='demo-admin@example.local'))
        if db.scalar(select(AuditEvent.id).where(AuditEvent.action=='demo.phase2.complete')):
            print('Démonstration phase 2 déjà présente ; aucune donnée réécrite.');return
        if db.scalar(select(Partner.id)):
            raise SystemExit('Organisations existantes : démonstration partenaires refusée pour préserver leurs données.')
        before=set(STORAGE.iterdir())
        try:
            for i,letter in enumerate(('A','B')):
                launch=db.scalar(select(Launch).where(Launch.order_ref==f'CMD-DEMO-00{i+1}'))
                client=Partner(name=f'Client fictif {letter}',kind='client');supplier=Partner(name=f'Fournisseur fictif {letter}',kind='supplier');db.add_all([client,supplier]);db.flush()
                accounts={}
                for org,kind in ((client,'client'),(supplier,'supplier')):
                    account=PartnerAccount(partner_id=org.id,email=f'demo-{kind}-{letter.lower()}@example.local',password_hash=hash_password(password));db.add(account)
                    role=PartnerRole(partner_id=org.id,name='Contributeur DÉMO',permissions_json=json.dumps(['read','message.write']+(['document.write','delivery.write'] if kind=='supplier' else [])));db.add(role);db.flush()
                    db.add(PartnerRoleAssignment(account_id=account.id,role_id=role.id));accounts[kind]=account
                root=BusinessOrder(client_id=client.id,reference=launch.order_ref,created_by=admin.id);db.add(root);db.flush();db.add(BusinessOrderLaunch(order_id=root.id,launch_id=launch.id,linked_by=admin.id))
                from .order_documents import adopt_launch
                db.flush();adopt_launch(db,launch.id,root.id)
                request=PartnerRequest(partner_id=supplier.id,launch_id=launch.id,order_ref=launch.order_ref,title='Bon matière DÉMO',doc_type='Bon de livraison',status='approved',created_by=admin.id);db.add(request);db.flush()
                doc,version=add_doc(db,launch,admin,'Bon matière DÉMO','Bon de livraison',b'DEMONSTRATION : quantite 40 m, document fournisseur fictif','bon-demo.txt')
                submission=PartnerSubmission(request_id=request.id,number=1,account_id=accounts['supplier'].id,original_name=version.original_name,disk_name=version.disk_name,sha256=version.sha256,size=version.size,content_type='text/plain',status='approved',reason='Vérification fictive pour démonstration',reviewed_by=admin.id);db.add(submission);db.flush()
                db.add(PartnerIntegration(submission_id=submission.id,version_id=version.id,integrated_by=admin.id))
                db.add(PartnerEvent(request_id=request.id,actor='staff:'+admin.id,kind='approved',message='Exemple fictif de validation fournisseur'))
                line=PartnerOrderLine(partner_id=supplier.id,launch_id=launch.id,order_ref=launch.order_ref,material_ref='TISSU-DEMO-'+letter,unit='m',ordered=Decimal('100'),created_by=admin.id);db.add(line);db.flush()
                for kind,quantity in [('planned','100'),('announced','40'),('declared','40'),('received','35')]:
                    db.add(PartnerDelivery(line_id=line.id,operation_key='demo-'+kind,kind=kind,quantity=Decimal(quantity),source_id=submission.id,actor=('partner:'+accounts['supplier'].id if kind in ('announced','declared') else 'staff:'+admin.id),note='Exemple fictif de réception partielle',occurred_on=date.today()))
                order=PartnerClientOrder(partner_id=client.id,launch_id=launch.id,reference=launch.order_ref,status='En préparation',confirmed_due=date.today()+timedelta(days=2));db.add(order);db.flush()
                db.add(PartnerClientOrderEvent(order_id=order.id,actor_id=admin.id,message='Commande fictive autorisée pour démonstration'))
                public_doc,public_version=add_doc(db,launch,admin,'Fiche client DÉMO','Fiche technique',b'Fiche client fictive sans tarif ni information fournisseur','client-demo.txt')
                db.add(DocumentReview(document_version_id=public_version.id,decision='approved',comment='Approbation fictive',reviewed_by=admin.id))
                pub=ClientPublication(launch_id=launch.id,document_version_id=public_version.id,client_name=client.name,reason='Publication fictive',created_by=admin.id);db.add(pub);db.flush()
                binding=PartnerPublication(partner_id=client.id,publication_id=pub.id);db.add(binding);db.flush()
                emit(db,client.id,'publication',binding.id,'publication','publication:'+binding.id,'Fiche client fictive publiée')
                pending=PartnerRequest(partner_id=supplier.id,launch_id=launch.id,order_ref=launch.order_ref,title='Certificat DÉMO attendu',doc_type='Certificat',due_date=date.today()+timedelta(days=1),created_by=admin.id);db.add(pending);db.flush()
                db.add(PartnerEvent(request_id=pending.id,actor='staff:'+admin.id,kind='requested',message='Demande documentaire fictive'))
            db.flush();generate_due(db)
            db.add(AuditEvent(actor_id=admin.id,action='demo.phase2.complete',target_type='demo',target_id='phase2',detail='{}'));db.commit()
        except Exception:
            db.rollback()
            for path in set(STORAGE.iterdir())-before:
                if path.is_file():path.unlink()
            raise
    print('DÉMO : admin demo-admin@example.local ; partenaires demo-client-a, demo-client-b, demo-supplier-a, demo-supplier-b @example.local. Mot de passe fourni par environnement. Aucun email envoyé.')

if __name__=='__main__':main()

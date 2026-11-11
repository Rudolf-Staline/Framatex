"""Completeness rooted in the order, including documents with no launch."""
from datetime import timedelta
from sqlalchemy import select
from .core import utcnow
from .models import Document,Folder
from .order_documents import OrderCompleteness,OrderDossier
from .completeness_models import CompletenessProfile
from .partner_phase2_models import RequirementPolicy
from .completeness import PHASE_RANK
from .sharing_routes import is_approved
from .partner_integration_routes import business_available


def evaluate(db,order,user,permitted):
    context=db.get(OrderCompleteness,order.id)
    profile=db.get(CompletenessProfile,context.profile_id) if context and context.profile_id else None
    root=db.scalar(select(OrderDossier).where(OrderDossier.order_id==order.id))
    phase=context.phase if context else 'preparation';items=[]
    for rule in profile.rules if profile else []:
        if not rule.active or not permitted(user,'document.read',rule.folder_slug):continue
        policy=db.get(RequirementPolicy,rule.id)
        optional=bool(policy and policy.optional)
        applicable=not policy or not policy.order_type or policy.order_type==context.order_type
        deadline=order.created_at.date()+timedelta(days=policy.days_after_launch) if policy and policy.days_after_launch is not None else None
        due=applicable and not optional and PHASE_RANK[phase]>=PHASE_RANK[rule.due_phase] and (deadline is None or utcnow().date()>=deadline)
        docs=list(db.scalars(select(Document).join(Folder).where(Folder.dossier_id==root.id,Folder.slug==rule.folder_slug,Document.doc_type==rule.document_type))) if root else []
        versions=[(d,max(d.versions,key=lambda v:v.number)) for d in docs if d.versions]
        versions=[(d,v) for d,v in versions if business_available(db,v.id)]
        accepted=[(d,v) for d,v in versions if not rule.requires_validation or is_approved(db,v,d)]
        if policy and policy.requires_client_publication:
            from .sharing_models import ClientPublication
            accepted=[(d,v) for d,v in accepted if db.scalar(select(ClientPublication.id).where(ClientPublication.document_version_id==v.id,ClientPublication.status=='published'))]
        status='not_applicable' if not applicable else 'ready' if accepted else 'pending_validation' if versions else 'missing'
        items.append({'rule_id':rule.id,'title':rule.title,'folder':rule.folder_slug,'doc_type':rule.document_type,'status':status,'due':due,'optional':optional,'deadline':deadline,'documents':[d.id for d,v in versions],'guidance':rule.guidance})
    return {'order_id':order.id,'configured':bool(profile),'profile_id':profile.id if profile else None,'phase':phase,'order_type':context.order_type if context else '',
            'items':items,'counts':{status:sum(i['status']==status and i['due'] for i in items) for status in ('missing','pending_validation','ready')},
            'business_rules_confirmed':False,'notice':'Règles configurables ; validation métier Framatex requise. Les délais historiques nommés days_after_launch sont ici calculés depuis la création de la commande.'}

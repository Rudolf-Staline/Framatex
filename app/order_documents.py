"""Canonical order dossier and conservative compatibility with historical launches."""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import ForeignKey, String, DateTime, select, update
from sqlalchemy.orm import Mapped, mapped_column, Session, object_session
from .core import Base, utcnow
from .models import uid, Document, DocumentVersion

SECTIONS = [('jaune','Technique et commercial'),('rose','Réception'),('bleu','Douane'),('vert','Facturation Framatex')]

class OrderDossier(Base):
    __tablename__ = 'order_dossiers'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey('business_orders.id'), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class OrderMember(Base):
    __tablename__ = 'order_members'
    order_id: Mapped[str] = mapped_column(ForeignKey('business_orders.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)


def dossier(db, order_id):
    # Lock the owning order before the read/create sequence. The unique constraint
    # independently protects against callers bypassing this service.
    from .partner_phase2_models import BusinessOrder
    from .models import Folder
    db.execute(update(BusinessOrder).where(BusinessOrder.id == order_id).values(id=order_id))
    row = db.scalar(select(OrderDossier).where(OrderDossier.order_id == order_id))
    if not row:
        row = OrderDossier(order_id=order_id); db.add(row); db.flush()
        for slug, label in SECTIONS:
            db.add(Folder(dossier_id=row.id, slug=slug, label=label))
        db.flush()
    return row


def launch_order(db, launch_id):
    from .partner_phase2_models import BusinessOrderLaunch
    return db.get(BusinessOrderLaunch, launch_id)


def folders_for_launch(db, launch):
    from .models import Folder
    link = launch_order(db, launch.id)
    if link:
        root = db.scalar(select(OrderDossier).where(OrderDossier.order_id == link.order_id))
        return list(db.scalars(select(Folder).where(Folder.dossier_id == root.id))) if root else []
    return launch.legacy_folders


def adopt_launch(db, launch_id, order_id):
    """Move only section FKs; version IDs, files and all referencing tables stay intact."""
    from .models import Folder, Document
    root = dossier(db, order_id)
    targets = {f.slug:f.id for f in db.scalars(select(Folder).where(Folder.dossier_id == root.id))}
    for old in db.scalars(select(Folder).where(Folder.launch_id == launch_id)):
        if old.slug not in targets:
            raise HTTPException(409, 'Rubrique historique inconnue : conversion manuelle requise')
        db.execute(update(Document).where(Document.folder_id == old.id).values(folder_id=targets[old.slug], launch_id=launch_id))
        old.canonical_id = targets[old.slug]  # immutable legacy section identifiers remain resolvable
    db.flush(); db.expire_all()


def order_access_clause(user, order_id=None):
    """SQL equivalent of the canonical ACL, usable before count/pagination.

    A launch attachment never grants order membership. Historical launch
    restrictions remain an additional condition on launch-owned documents.
    """
    from sqlalchemy import exists, or_, false, true
    from sqlalchemy.orm import aliased
    from .partner_phase2_models import BusinessOrder
    from .access import is_admin
    if not user.active:
        return false()
    if is_admin(user):
        return true()
    order = aliased(BusinessOrder)
    member = aliased(OrderMember)
    target = BusinessOrder.id if order_id is None else order_id
    return exists(select(order.id).where(order.id == target, or_(
        order.created_by == user.id,
        exists(select(member.order_id).where(member.order_id == order.id, member.user_id == user.id)))))


def source_launch_access_clause(user, launch_id):
    """Historical launch ACL only; deliberately independent of order grants."""
    from sqlalchemy import exists, or_, false, true
    from sqlalchemy.orm import aliased
    from .models import Launch, LaunchMember
    from .access import is_admin
    if not user.active:
        return false()
    if is_admin(user):
        return true()
    launch, member = aliased(Launch), aliased(LaunchMember)
    return exists(select(launch.id).where(launch.id == launch_id, or_(
        launch.restricted.is_(False), launch.created_by == user.id,
        exists(select(member.id).where(member.launch_id == launch.id, member.user_id == user.id)))).correlate_except(launch))


def document_access_clause(user, document=None):
    """Document ACL in SQL, independent of selected joins and ORM loading."""
    from sqlalchemy import exists, and_, or_
    from sqlalchemy.orm import aliased
    from .models import Folder
    document = Document if document is None else document
    folder, root = aliased(Folder), aliased(OrderDossier)
    canonical = and_(folder.dossier_id.is_not(None), exists(select(root.id).where(
        root.id == folder.dossier_id, order_access_clause(user, root.order_id))),
        or_(document.launch_id.is_(None), source_launch_access_clause(user, document.launch_id)))
    legacy = and_(folder.dossier_id.is_(None), source_launch_access_clause(user, folder.launch_id))
    return exists(select(folder.id).where(folder.id == document.folder_id, or_(canonical, legacy)))


def order_accessible(db, user, order_id):
    from .partner_phase2_models import BusinessOrder
    return db.scalar(select(BusinessOrder.id).where(BusinessOrder.id == order_id,
        order_access_clause(user, BusinessOrder.id))) is not None


def must_order(db, user, order_id):
    from .partner_phase2_models import BusinessOrder
    if not order_accessible(db,user,order_id): raise HTTPException(404, 'Commande introuvable')
    return db.get(BusinessOrder, order_id)


def document_accessible(db, user, doc):
    if doc is None or not user.active:
        return False
    from .access import accessible_launch
    from .models import Launch
    if doc.folder.dossier_id:
        root = db.get(OrderDossier, doc.folder.dossier_id)
        return bool(root and order_accessible(db, user, root.order_id) and
                    (not doc.launch_id or accessible_launch(db, user, db.get(Launch, doc.launch_id))))
    return accessible_launch(db, user, doc.folder.launch)


def document_order_id(db, doc):
    root=db.get(OrderDossier, doc.folder.dossier_id) if doc.folder.dossier_id else None
    return root.order_id if root else None


def document_in_launch(db, doc, launch_id):
    from .models import Launch
    launch=db.get(Launch,launch_id)
    return bool(launch and doc and doc.launch_id in (None, launch_id) and doc.folder_id in {f.id for f in launch.folders})


def folder_ids(db, launch_id):
    from .models import Launch
    launch=db.get(Launch,launch_id)
    return [f.id for f in launch.folders] if launch else []


class OrderCompleteness(Base):
    __tablename__='order_completeness'
    order_id: Mapped[str]=mapped_column(ForeignKey('business_orders.id'),primary_key=True)
    profile_id: Mapped[str | None]=mapped_column(ForeignKey('completeness_profiles.id'),nullable=True)
    phase: Mapped[str]=mapped_column(String(30),default='preparation')
    order_type: Mapped[str]=mapped_column(String(100),default='')


def get_doc(db: Session, doc_id: str) -> Document:
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, "Document introuvable")
    return d


def version_out(v: DocumentVersion):
    return {"id": v.id, "number": v.number, "original_name": v.original_name, "size": v.size, "sha256": v.sha256, "created_at": v.created_at.isoformat(), "uploaded_by": v.uploaded_by}


def doc_out(d: Document):
    versions = sorted(d.versions, key=lambda v: v.number)
    from .document_types import type_out
    return {"classification": type_out(object_session(d),d), "order_id": document_order_id(object_session(d), d), "launch_id": d.launch_id, "id": d.id, "title": d.title, "doc_type": d.doc_type, "folder": d.folder.slug, "created_at": d.created_at.isoformat(), "versions": [version_out(v) for v in versions], "latest": version_out(versions[-1]) if versions else None}

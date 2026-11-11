"""Canonical order dossier and conservative compatibility with historical launches."""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import ForeignKey, String, DateTime, select, update
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid

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


def order_accessible(db, user, order_id):
    from .partner_phase2_models import BusinessOrder, BusinessOrderLaunch
    from .models import Launch
    from .access import accessible_launch
    order = db.get(BusinessOrder, order_id)
    if not order or not user.active: return False
    if any(r.name == 'Administrateur' for r in user.roles): return True
    launches = list(db.scalars(select(Launch).join(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id == order_id)))
    # Never widen historical restricted launch access by linking an order.
    if launches: return all(accessible_launch(db, user, l) for l in launches)
    return order.created_by == user.id or db.get(OrderMember, (order_id,user.id)) is not None


def must_order(db, user, order_id):
    from .partner_phase2_models import BusinessOrder
    if not order_accessible(db,user,order_id): raise HTTPException(404, 'Commande introuvable')
    return db.get(BusinessOrder, order_id)


def document_accessible(db, user, doc):
    from .access import accessible_launch
    if doc.folder.dossier_id:
        root=db.get(OrderDossier, doc.folder.dossier_id)
        return order_accessible(db,user,root.order_id)
    return accessible_launch(db,user,doc.folder.launch)


def document_order_id(db, doc):
    root=db.get(OrderDossier, doc.folder.dossier_id) if doc.folder.dossier_id else None
    return root.order_id if root else None


def document_in_launch(db, doc, launch_id):
    from .models import Launch
    launch=db.get(Launch,launch_id)
    return bool(launch and doc and doc.folder_id in {f.id for f in launch.folders})


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

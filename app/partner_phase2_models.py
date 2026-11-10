"""Additive phase 2 metadata, organization-scoped roles and document provenance."""
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base, utcnow
from .models import uid

class PartnerProfile(Base):
    __tablename__='partner_profiles'
    partner_id: Mapped[str]=mapped_column(ForeignKey('partners.id'),primary_key=True)
    trade_name: Mapped[str]=mapped_column(String(150),default='')
    address: Mapped[str]=mapped_column(Text,default='')
    domains_json: Mapped[str]=mapped_column(Text,default='[]')
    administrative_json: Mapped[str]=mapped_column(Text,default='{}')

class PartnerRole(Base):
    __tablename__='partner_roles'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    partner_id: Mapped[str]=mapped_column(ForeignKey('partners.id'),index=True)
    name: Mapped[str]=mapped_column(String(100))
    permissions_json: Mapped[str]=mapped_column(Text)

class PartnerRoleAssignment(Base):
    __tablename__='partner_role_assignments'
    account_id: Mapped[str]=mapped_column(ForeignKey('partner_accounts.id'),primary_key=True)
    role_id: Mapped[str]=mapped_column(ForeignKey('partner_roles.id'))

class PartnerIntegration(Base):
    __tablename__='partner_integrations'
    submission_id: Mapped[str]=mapped_column(ForeignKey('partner_submissions.id'),primary_key=True)
    version_id: Mapped[str]=mapped_column(ForeignKey('document_versions.id'),unique=True)
    integrated_by: Mapped[str]=mapped_column(ForeignKey('users.id'))
    integrated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    withdrawal_reason: Mapped[str]=mapped_column(Text,default='')

class ConfirmedDatumSource(Base):
    __tablename__='partner_confirmed_datum_sources'
    datum_id: Mapped[str]=mapped_column(ForeignKey('document_data.id'),primary_key=True)
    confirmed_id: Mapped[str]=mapped_column(ForeignKey('confirmed_extracted_fields.id'))

from datetime import date
from sqlalchemy import Date, Integer, UniqueConstraint, CheckConstraint

class PartnerClientOrder(Base):
    __tablename__='partner_client_orders'
    __table_args__=(UniqueConstraint('partner_id','launch_id'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    partner_id: Mapped[str]=mapped_column(ForeignKey('partners.id'),index=True)
    launch_id: Mapped[str]=mapped_column(ForeignKey('launches.id'))
    reference: Mapped[str]=mapped_column(String(100))
    status: Mapped[str]=mapped_column(String(40),default='Non renseigné')
    confirmed_due: Mapped[date | None]=mapped_column(Date,nullable=True)
    active: Mapped[bool]=mapped_column(Boolean,default=True)

class PartnerThread(Base):
    __tablename__='partner_threads'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    order_id: Mapped[str]=mapped_column(ForeignKey('partner_client_orders.id'),index=True)
    title: Mapped[str]=mapped_column(String(200))
    status: Mapped[str]=mapped_column(String(20),default='open')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class PartnerMessage(Base):
    __tablename__='partner_messages'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    thread_id: Mapped[str]=mapped_column(ForeignKey('partner_threads.id'),index=True)
    author: Mapped[str]=mapped_column(String(80))
    text: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class PartnerAttachment(Base):
    __tablename__='partner_attachments'
    __table_args__=(CheckConstraint('(event_id IS NOT NULL AND message_id IS NULL) OR (event_id IS NULL AND message_id IS NOT NULL)'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    partner_id: Mapped[str]=mapped_column(ForeignKey('partners.id'),index=True)
    event_id: Mapped[str | None]=mapped_column(ForeignKey('partner_events.id'),nullable=True)
    message_id: Mapped[str | None]=mapped_column(ForeignKey('partner_messages.id'),nullable=True)
    owner: Mapped[str]=mapped_column(String(80))
    classification: Mapped[str]=mapped_column(String(30),default='partner_private')
    original_name: Mapped[str]=mapped_column(String(240))
    disk_name: Mapped[str]=mapped_column(String(64),unique=True)
    sha256: Mapped[str]=mapped_column(String(64))
    size: Mapped[int]=mapped_column(Integer)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

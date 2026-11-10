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

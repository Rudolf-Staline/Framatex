"""Personal learning data only; owner namespace separates employees and partners."""
from datetime import datetime
from sqlalchemy import String,Integer,DateTime,Boolean,Text
from sqlalchemy.orm import Mapped,mapped_column
from .core import Base,utcnow
from .models import uid

class GuideProgress(Base):
    __tablename__='guide_progress'
    owner:Mapped[str]=mapped_column(String(60),primary_key=True)
    tour_id:Mapped[str]=mapped_column(String(100),primary_key=True)
    version:Mapped[int]=mapped_column(Integer,primary_key=True)
    step:Mapped[int]=mapped_column(Integer,default=0)
    status:Mapped[str]=mapped_column(String(20),default='started')
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class GuidePreference(Base):
    __tablename__='guide_preferences'
    owner:Mapped[str]=mapped_column(String(60),primary_key=True)
    automatic:Mapped[str]=mapped_column(String(20),default='new')
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class GuideVisit(Base):
    __tablename__='guide_visits'
    owner:Mapped[str]=mapped_column(String(60),primary_key=True)
    procedure_id:Mapped[str]=mapped_column(String(100),primary_key=True)
    views:Mapped[int]=mapped_column(Integer,default=1)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class GuideFeedback(Base):
    __tablename__='guide_feedback'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    owner:Mapped[str]=mapped_column(String(60),index=True)
    procedure_id:Mapped[str | None]=mapped_column(String(100),nullable=True)
    helpful:Mapped[bool]=mapped_column(Boolean)
    reason:Mapped[str]=mapped_column(String(30),default='none')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class GuideEvent(Base):
    __tablename__='guide_events'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    owner:Mapped[str]=mapped_column(String(60),index=True)
    kind:Mapped[str]=mapped_column(String(30))
    target:Mapped[str]=mapped_column(String(120),default='')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class GuideBudget(Base):
    __tablename__='guide_budgets'
    key:Mapped[str]=mapped_column(String(150),primary_key=True)
    used:Mapped[int]=mapped_column(Integer,default=0)

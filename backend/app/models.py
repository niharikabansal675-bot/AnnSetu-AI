from __future__ import annotations
import secrets
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(130))
    email: Mapped[str] = mapped_column(String(250), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(350))
    role: Mapped[str] = mapped_column(String(20))
    organisation: Mapped[str] = mapped_column(String(180), default='')
    locality: Mapped[str] = mapped_column(String(100), default='Ghaziabad')
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Donation(Base):
    __tablename__ = 'donations'
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(150))
    food_type: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer)
    locality: Mapped[str] = mapped_column(String(90))
    address: Mapped[str] = mapped_column(String(300))
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    storage: Mapped[str] = mapped_column(String(160))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(25), default='available')
    accepted_ngo_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    qr_token: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: secrets.token_urlsafe(36))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class CollectorTracking(Base):
    __tablename__ = 'collector_tracking'
    donation_id: Mapped[int] = mapped_column(ForeignKey('donations.id'), primary_key=True)
    collector_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    sharing: Mapped[bool] = mapped_column(Boolean, default=False)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    accuracy_m: Mapped[float | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class DeliveryReceipt(Base):
    __tablename__ = 'delivery_receipts'
    donation_id: Mapped[int] = mapped_column(ForeignKey('donations.id'), primary_key=True)
    confirmed_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    receiver_name: Mapped[str] = mapped_column(String(130))
    received_quantity: Mapped[int] = mapped_column(Integer)
    condition: Mapped[str] = mapped_column(String(25))
    notes: Mapped[str] = mapped_column(String(500), default='')
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Offer(Base):
    __tablename__ = 'offers'
    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int] = mapped_column(ForeignKey('donations.id'))
    ngo_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    reason: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int | None] = mapped_column(ForeignKey('donations.id'), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    actor: Mapped[str] = mapped_column(String(35))
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

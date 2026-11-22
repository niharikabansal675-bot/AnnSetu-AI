"""Backwards-compatible entry point for `uvicorn main:app` and existing scripts.

New code should import directly from `app.database`, `app.models`, etc.
"""
from app.main import app
from app.database import Base, engine, SessionLocal, db_session
from app.models import User, Donation, Offer, Audit, CollectorTracking, DeliveryReceipt
from app.security import password_hash, check_password, utcnow, aware, token_for
from app.routers.coordinator import run_coordinator

from __future__ import annotations

import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine, event, select, text, func
from sqlalchemy.orm import Session
from fastapi import HTTPException

# Executed from backend/tests or directly with python absolute/path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, engine as app_engine
from app.models import Audit, Donation, Offer, User
from app.routers.offers import respond
from app.schemas import OfferAction
from app.security import utcnow


def require_local_postgres():
    url = app_engine.url
    if app_engine.dialect.name != "postgresql":
        raise RuntimeError("STOP: DATABASE_URL is not PostgreSQL. Start your local PostgreSQL backend first.")
    if (url.host or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("STOP: This test refuses remote/production PostgreSQL connections.")
    return url


def create_isolated_engine(schema: str):
    # Separate connection pool, so the application's main pool remains untouched.
    isolated = create_engine(app_engine.url, pool_pre_ping=True, pool_size=5, max_overflow=0)

    @event.listens_for(isolated, "checkout")
    def set_search_path(dbapi_connection, connection_record, connection_proxy):
        cursor = dbapi_connection.cursor()
        try:
            # `schema` is generated internally, never provided by a user.
            cursor.execute(f'SET search_path TO "{schema}", public')
        finally:
            cursor.close()

    return isolated


def seed(db: Session, *, distinct_offers: bool):
    prefix = uuid.uuid4().hex[:12]
    provider = User(name="Race Provider", email=f"provider_{prefix}@example.invalid", password_hash="x", role="provider", organisation="Synthetic Provider", is_demo=True)
    ngos = [User(name=f"NGO {i}", email=f"ngo{i}_{prefix}@example.invalid", password_hash="x", role="ngo", organisation=f"Synthetic NGO {i}", capacity=100, verified=True, is_demo=True) for i in range(2 if distinct_offers else 1)]
    db.add_all([provider, *ngos]); db.flush()
    now = utcnow()
    donation = Donation(provider_id=provider.id, title="Synthetic concurrency test", food_type="Vegetarian", quantity=20, locality="Ghaziabad", address="Synthetic only", prepared_at=now, storage="Covered", deadline=now+timedelta(hours=4), status="available", is_demo=True)
    db.add(donation); db.flush()
    offers = [Offer(donation_id=donation.id, ngo_id=ngo.id, status="pending", expires_at=now+timedelta(minutes=15)) for ngo in ngos]
    db.add_all(offers); db.flush()
    ids = (donation.id, [o.id for o in offers], [n.id for n in ngos])
    db.commit()
    return ids


def concurrently_accept(engine, donation_id, offer_ids, ngo_ids):
    gate = threading.Barrier(2, timeout=15)
    def attempt(index):
        with Session(engine, expire_on_commit=False) as db:
            ngo_id = ngo_ids[index] if len(ngo_ids) > 1 else ngo_ids[0]
            user = db.get(User, ngo_id)
            offer_id = offer_ids[index] if len(offer_ids) > 1 else offer_ids[0]
            gate.wait()
            try:
                result = respond(offer_id, OfferAction(decision="accept"), user, db)
                return ("accepted", result["status"])
            except HTTPException as exc:
                db.rollback()
                return ("rejected", exc.status_code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, i) for i in range(2)]
        results = [f.result(timeout=25) for f in futures]
    with Session(engine) as db:
        donation = db.get(Donation, donation_id)
        offers = db.scalars(select(Offer).where(Offer.donation_id == donation_id)).all()
        accepted = [o for o in offers if o.status == "accepted"]
        audit_count = db.scalar(select(func.count(Audit.id)).where(Audit.donation_id == donation_id, Audit.action == "offer_accepted"))
        assert results.count(("accepted", "accepted")) == 1, f"Expected exactly one successful acceptance; got {results}"
        assert results.count(("rejected", 409)) == 1, f"Expected one conflict (409); got {results}"
        assert donation.status == "accepted", f"Donation state: {donation.status}"
        assert len(accepted) == 1, f"Accepted offer count: {len(accepted)}"
        assert donation.accepted_ngo_id == accepted[0].ngo_id, "Mismatch between accepted NGO and accepted offer"
        assert audit_count == 1, f"Expected one accepted audit event; got {audit_count}"
        assert all(o.status != "pending" for o in offers), "A second pending offer remained after acceptance"
        return results


def main():
    require_local_postgres()
    schema = "annsetu_race_" + uuid.uuid4().hex[:16]
    isolated = None
    created = False
    try:
        with app_engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True
        isolated = create_isolated_engine(schema)
        Base.metadata.create_all(isolated)
        print("Temporary isolated PostgreSQL schema created; existing public data is untouched.", flush=True)
        with Session(isolated) as db:
            donation_id, offers, ngos = seed(db, distinct_offers=False)
        results = concurrently_accept(isolated, donation_id, offers, ngos)
        print("PASS 1/2: Two simultaneous attempts to accept the SAME offer =>", results)
        with Session(isolated) as db:
            donation_id, offers, ngos = seed(db, distinct_offers=True)
        results = concurrently_accept(isolated, donation_id, offers, ngos)
        print("PASS 2/2: Two different NGOs simultaneously accept TWO offers on one donation =>", results)
        print("RESULT: 2/2 PostgreSQL acceptance race tests passed.")
    finally:
        if isolated is not None:
            isolated.dispose()
        if created:
            with app_engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            print("Temporary test schema removed.")


if __name__ == "__main__":
    main()

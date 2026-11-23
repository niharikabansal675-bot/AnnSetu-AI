
from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from test_pg_concurrency_isolated import (
    Base, Audit, Donation, Offer, User, app_engine,
    create_isolated_engine, require_local_postgres,
)
from app.agents.T3.actions import execute_planned_offer
from app.agents.T3.graph import evaluate_donation
from app.security import utcnow


def seed_for_t3(db: Session) -> int:
    tag = uuid.uuid4().hex[:12]
    provider = User(
        name="T3 Race Provider", email=f"t3_provider_{tag}@example.invalid",
        password_hash="x", role="provider", organisation="Synthetic Provider",
        locality="Ghaziabad", is_demo=True,
    )
    ngo = User(
        name="T3 Race NGO", email=f"t3_ngo_{tag}@example.invalid",
        password_hash="x", role="ngo", organisation="Synthetic NGO",
        locality="Ghaziabad", capacity=100, verified=True, is_demo=True,
    )
    db.add_all([provider, ngo])
    db.flush()
    now = utcnow()
    donation = Donation(
        provider_id=provider.id, title="Synthetic T3 creation race",
        food_type="Vegetarian", quantity=20, locality="Ghaziabad",
        address="Synthetic only", prepared_at=now, storage="Covered",
        deadline=now + timedelta(hours=4), status="available", is_demo=True,
    )
    db.add(donation)
    db.flush()
    donation_id = donation.id
    db.commit()
    return donation_id


def run_two_workers(isolated, donation_id: int):
    # Each worker independently plans, then both race to execute the same
    # donation. Build plans before starting the database write race.
    proposals = []
    for _ in range(2):
        with Session(isolated) as db:
            proposal = evaluate_donation(db, donation_id, include_road=False)
            proposals.append(proposal)
            db.rollback()

    for i, proposal in enumerate(proposals, 1):
        state = proposal.state
        if not (
            state.proposed_action == "offer"
            and state.proposed_ngo_id is not None
            and state.phase == "verified"
            and proposal.nodes_visited == ("observe", "evaluate", "plan", "verify")
            and not state.errors
        ):
            raise AssertionError(
                f"Worker {i} did not generate an eligible offer proposal. "
                f"This is a fixture/planner issue, not a concurrency failure. "
                f"State: {state.as_dict()}"
            )

    gate = threading.Barrier(2, timeout=15)

    def attempt(proposal):
        with Session(isolated, expire_on_commit=False) as db:
            gate.wait()
            try:
                outcome = execute_planned_offer(db, proposal, enable_writes=True)
                return outcome.status, outcome.reason, outcome.offer_id
            finally:
                db.rollback()  # release a read transaction on skipped results

    with ThreadPoolExecutor(max_workers=2) as pool:
        fs = [pool.submit(attempt, p) for p in proposals]
        results = [f.result(timeout=30) for f in fs]

    with Session(isolated) as db:
        offers = db.scalars(select(Offer).where(Offer.donation_id == donation_id)).all()
        audit_count = db.scalar(
            select(func.count(Audit.id)).where(
                Audit.donation_id == donation_id,
                Audit.action == "t3_offer_created",
            )
        )
        pending = [o for o in offers if o.status == "pending"]
        assert len(pending) == 1, f"Expected one pending offer, found {len(pending)}"
        assert len(offers) == 1, f"Expected only one offer total, found {len(offers)}"
        assert audit_count == 1, f"Expected one t3_offer_created audit, found {audit_count}"
        assert sorted(status for status, _, _ in results) == ["created", "skipped"], results
        return results


def main():
    require_local_postgres()
    schema = "annsetu_t3_race_" + uuid.uuid4().hex[:16]
    isolated = None
    created = False
    try:
        with app_engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True
        isolated = create_isolated_engine(schema)
        Base.metadata.create_all(isolated)
        print("Temporary isolated PostgreSQL schema created.", flush=True)
        with Session(isolated) as db:
            donation_id = seed_for_t3(db)
        results = run_two_workers(isolated, donation_id)
        print("PASS: Two T3 workers raced to create one donation offer =>", results)
        print("RESULT: 1/1 T3 offer-creation concurrency test passed.")
    finally:
        if isolated is not None:
            isolated.dispose()
        if created:
            with app_engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            print("Temporary test schema removed.")


if __name__ == "__main__":
    main()

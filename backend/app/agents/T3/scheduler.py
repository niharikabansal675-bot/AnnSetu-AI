from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Donation
from .graph import evaluate_donation
from .recovery import reconcile_demo_offers
from .actions import execute_planned_offer


def cycle_demo_donations(db: Session, *, write: bool = False, limit: int = 25) -> dict:
    """Inspect at most `limit` available DEMO donations, optionally create offers.

    No real donation is inspected for execution or modified. Errors for one
    donation are rolled back and don't prevent later donations being processed.
    A production operator must not enable writes before PostgreSQL concurrency
    tests; the caller also enforces the explicit execution feature flag.
    """
    if not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    if write and (db.bind is None or db.bind.dialect.name != 'postgresql'):
        raise RuntimeError('T3 offer writes require PostgreSQL')

    ids = list(db.scalars(
        select(Donation.id)
        .where(Donation.status == 'available', Donation.is_demo.is_(True))
        .order_by(Donation.created_at, Donation.id)
        .limit(limit)
    ).all())
    # End the initial read transaction before handling each donation separately.
    db.rollback()
    report = {'mode': 'demo_write' if write else 'preview', 'processed': 0,
              'offers_created': [], 'waiting': [], 'skipped': [], 'errors': []}
    for donation_id in ids:
        try:
            if write:
                outcome = reconcile_demo_offers(db, donation_id)
                if outcome.status != 'ready':
                    report['waiting' if outcome.status == 'waiting' else 'skipped'].append(
                        {'donation_id': donation_id, 'reason': outcome.status})
                    db.rollback()
                    report['processed'] += 1
                    continue
            proposal = evaluate_donation(db, donation_id, include_road=False)
            if write and proposal.state.proposed_action == 'offer':
                result = execute_planned_offer(db, proposal, enable_writes=True)
                if result.status == 'created':
                    report['offers_created'].append({'donation_id': donation_id,
                                                     'ngo_id': result.ngo_id, 'offer_id': result.offer_id})
                else:
                    report['skipped'].append({'donation_id': donation_id, 'reason': result.reason})
            else:
                report['skipped'].append({'donation_id': donation_id,
                                          'reason': proposal.state.proposed_action})
            # A read-only preview never persists anything, including autoflush.
            db.rollback()
            report['processed'] += 1
        except Exception as exc:
            db.rollback()
            report['errors'].append({'donation_id': donation_id, 'error_type': type(exc).__name__})
    return report

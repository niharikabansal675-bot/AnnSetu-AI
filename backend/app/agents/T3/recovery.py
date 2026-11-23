from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import Audit, Donation, Offer
from ...security import aware, utcnow


@dataclass(frozen=True)
class RecoveryResult:
    donation_id: int
    status: str  # ready | waiting | stopped | not_found | forbidden
    timed_out_offer_ids: tuple[int, ...] = ()
    reason: str = ''


def reconcile_demo_offers(db: Session, donation_id: int) -> RecoveryResult:
    """Expire overdue demo offers with transactionally auditable changes.

    PostgreSQL locks the donation row before checking any offers. SQLite is
    suitable only for isolated unit tests: it cannot test concurrency locks.
    No new offers are created, and real donations are never changed.
    """
    if donation_id <= 0:
        return RecoveryResult(donation_id, 'not_found', reason='Invalid donation ID.')

    donation = db.scalar(select(Donation).where(Donation.id == donation_id).with_for_update())
    if donation is None:
        return RecoveryResult(donation_id, 'not_found', reason='Donation not found.')
    db.refresh(donation)
    if not donation.is_demo:
        return RecoveryResult(donation_id, 'forbidden', reason='Only demo donations are supported.')
    if donation.status != 'available' or donation.accepted_ngo_id is not None:
        return RecoveryResult(donation_id, 'stopped', reason='Donation is not available for matching.')

    now = utcnow()
    if aware(donation.deadline) <= now:
        return RecoveryResult(donation_id, 'stopped', reason='Donation deadline has passed.')

    pending = db.scalars(
        select(Offer).where(Offer.donation_id == donation_id, Offer.status == 'pending')
        .order_by(Offer.id.asc()).with_for_update()
    ).all()

    expired_ids = []
    active = False
    for offer in pending:
        if aware(offer.expires_at) <= now:
            offer.status = 'timed_out'
            offer.responded_at = now
            expired_ids.append(offer.id)
            db.add(Audit(
                donation_id=donation_id, actor='agent', actor_id=None,
                action='t3_offer_timed_out',
                detail=f'T3 reconciled expired offer {offer.id}; NGO will not be retried.',
            ))
        else:
            active = True

    if expired_ids:
        # Commit under the donation lock, before a fresh T3 eligibility check.
        # The action executor re-locks and rechecks after the evaluation.
        db.commit()
    if active:
        return RecoveryResult(donation_id, 'waiting', tuple(expired_ids),
                              'An active NGO offer is still awaiting a response.')
    return RecoveryResult(donation_id, 'ready', tuple(expired_ids),
                          'No active offer. A fresh T3 evaluation may proceed.')

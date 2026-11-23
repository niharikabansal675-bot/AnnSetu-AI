from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...config import GIS_RADIUS_KM
from ...models import Audit, Donation, Offer, User
from ...security import aware, utcnow
from .graph import GraphResult


@dataclass(frozen=True)
class ActionResult:
    status: str  # disabled | skipped | created
    reason: str
    donation_id: int
    offer_id: int | None = None
    ngo_id: int | None = None


def _location_ok(db: Session, donation: Donation, ngo: User) -> bool:
    """Validate the geographic eligibility using current DB data.

    Real donations MUST have PostGIS coordinates. Synthetic demo accounts
    without coordinates can use the pre-existing locality approximation.
    """
    if db.bind.dialect.name == 'postgresql':
        row = db.execute(text('''
            SELECT d.pickup_location IS NOT NULL AS has_pickup,
                CASE WHEN d.pickup_location IS NOT NULL AND u.location IS NOT NULL
                THEN ST_DWithin(u.location, d.pickup_location, :radius_m)
                ELSE FALSE END AS near
            FROM donations d JOIN users u ON u.id=:ngo_id
            WHERE d.id=:donation_id
        '''), {'ngo_id': ngo.id, 'donation_id': donation.id,
               'radius_m': GIS_RADIUS_KM * 1000}).mappings().one_or_none()
        if not row:
            return False
        if row['has_pickup']:
            return bool(row['near'])
        if not donation.is_demo:
            return False
    elif not donation.is_demo:
        # A real donation must never use SQLite/no-GIS as a fallback.
        return False

    if donation.is_demo:
        from ...routers.coordinator import locality_distance
        return locality_distance(donation.locality, ngo.locality) is not None
    return False


def execute_planned_offer(db: Session, proposal: GraphResult, *,
                          enable_writes: bool = False) -> ActionResult:
    """Create ONE pending offer, revalidating all important business rules.

    WARNING: a PostgreSQL row lock serialises T3 executions for one donation,
    but the legacy coordinator must not run simultaneously with this executor.
    Call with a fresh Session and no prior transaction when possible.

    A rejected plan does not write an audit row; successful actions are audited
    in the same commit as the offer. No external LLM controls permissions.
    """
    s = proposal.state
    if not enable_writes:
        return ActionResult('disabled', 'Offer writes require explicit opt-in.', s.donation_id)
    if (proposal.safe_to_execute or proposal.nodes_visited != ('observe', 'evaluate', 'plan', 'verify')
            or s.phase != 'verified'
            or s.proposed_action != 'offer' or s.proposed_ngo_id is None
            or s.errors or s.donation_id <= 0
            or s.pending_offer_id is not None
            or s.proposed_ngo_id not in {c.ngo_id for c in s.candidates}
            or s.proposed_ngo_id in s.previous_ngo_ids):
        return ActionResult('skipped', 'Proposal was not a valid verified dry-run offer.', s.donation_id)

    # The source of truth is always current database state, never the snapshot.
    # FOR UPDATE locks the donation row in PostgreSQL until transaction commit.
    d = db.scalar(select(Donation).where(Donation.id == s.donation_id).with_for_update())
    if d is None or d.status != 'available' or d.accepted_ngo_id is not None:
        return ActionResult('skipped', 'Donation is no longer available.', s.donation_id)
    # Step 6 rollout policy: writes are permitted for synthetic demo data ONLY.
    # The selected NGO is also required to be a demo record below.
    if not d.is_demo:
        return ActionResult('skipped', 'T3 execution is limited to demo donations.', d.id)
    now = utcnow()
    if aware(d.deadline) <= now + timedelta(minutes=30):
        return ActionResult('skipped', 'Pickup deadline is too close.', d.id)
    if d.quantity <= 0:
        return ActionResult('skipped', 'Invalid donation quantity.', d.id)

    # Any previous offer to this NGO (including decline/timeout) blocks replay.
    if db.scalar(select(Offer.id).where(Offer.donation_id == d.id,
                                        Offer.ngo_id == s.proposed_ngo_id).limit(1)) is not None:
        return ActionResult('skipped', 'NGO has already been offered this donation.', d.id)
    # An expired pending offer still needs to be explicitly reconciled by the
    # existing coordinator. Never silently overwrite it.
    if db.scalar(select(Offer.id).where(Offer.donation_id == d.id,
                                        Offer.status == 'pending').limit(1)) is not None:
        return ActionResult('skipped', 'Another pending offer exists.', d.id)
    ngo = db.get(User, s.proposed_ngo_id)
    if (ngo is None or ngo.role != 'ngo' or not ngo.verified
            or ngo.is_demo != d.is_demo or ngo.capacity < d.quantity):
        return ActionResult('skipped', 'NGO is no longer eligible.', d.id)
    if not _location_ok(db, d, ngo):
        return ActionResult('skipped', 'NGO location is no longer eligible.', d.id)

    # Even if the original plan used an OSRM ETA, it may be stale; the executor
    # enforces minimum buffer, while any tighter travel-time bound is checked
    # from the proposal only as an additional conservative constraint.
    selected = next(c for c in s.candidates if c.ngo_id == ngo.id)
    if (selected.road_duration_minutes is not None
            and aware(d.deadline) <= now + timedelta(minutes=max(30, selected.road_duration_minutes + 15))):
        return ActionResult('skipped', 'Planned road ETA no longer fits the deadline.', d.id)

    offer = Offer(donation_id=d.id, ngo_id=ngo.id, status='pending',
                  reason=('T3 bounded coordination: NGO verified, recorded capacity and '
                          'location rechecked at execution; NGO acceptance still required.'),
                  expires_at=min(now + timedelta(minutes=15), aware(d.deadline)))
    db.add(offer)
    db.flush()
    offer_id = offer.id
    db.add(Audit(donation_id=d.id, actor='agent', actor_id=None,
                 action='t3_offer_created',
                 detail=f'T3 created offer {offer_id} for eligible NGO id {ngo.id}; pending acceptance.'))
    db.commit()
    # Verify persistence after the commit. Avoid reporting success on failed writes.
    saved = db.get(Offer, offer_id)
    if saved is None or saved.status != 'pending' or saved.ngo_id != ngo.id:
        raise RuntimeError('Committed offer did not verify correctly')
    return ActionResult('created', 'Offer created and verified.', d.id, offer_id, ngo.id)

from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import db_session
from ..models import Donation, User
from ..security import current_user, require_role
from ..agents.T3.actions import execute_planned_offer
from ..agents.T3.graph import evaluate_donation

router = APIRouter(tags=['T3 Agent (controlled demo execution)'])


def _enabled() -> bool:
    return os.getenv('T3_DEMO_EXECUTION_ENABLED', 'false').strip().lower() == 'true'


@router.post('/api/admin/t3/execute/{donation_id}')
def t3_execute(
    donation_id: int,
    include_road: bool = Query(default=False, description='Optional bounded OSRM estimates'),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    require_role(user, 'admin')
    if not _enabled():
        raise HTTPException(status_code=403, detail='T3 demo execution is disabled')
    # Row locking and PostGIS are guaranteed only by the PostgreSQL backend.
    if db.bind is None or db.bind.dialect.name != 'postgresql':
        raise HTTPException(status_code=503, detail='T3 execution requires PostgreSQL')
    if donation_id <= 0:
        raise HTTPException(status_code=404, detail='Donation not found')
    d = db.get(Donation, donation_id)
    if d is None:
        raise HTTPException(status_code=404, detail='Donation not found')
    if not d.is_demo:
        raise HTTPException(status_code=403, detail='T3 execution is demo-only')

    try:
        proposal = evaluate_donation(db, donation_id, include_road=include_road)
        if proposal.state.proposed_action != 'offer':
            return {
                'mode': 'controlled_demo',
                'decision': proposal.state.proposed_action,
                'write_status': 'skipped',
                'reason': 'No verified offer proposal. No offer was created.',
                'proposal': proposal.as_dict(),
            }
        # Revalidation + row lock + commit + audit happen in the action layer.
        result = execute_planned_offer(db, proposal, enable_writes=True)
    except Exception:
        db.rollback()
        # Do not reveal private DB details or stack traces in API responses.
        raise HTTPException(status_code=503, detail='T3 execution failed safely') from None

    return {
        'mode': 'controlled_demo',
        'decision': proposal.state.proposed_action,
        'write_status': result.status,
        'reason': result.reason,
        'donation_id': result.donation_id,
        'offer_created': result.status == 'created',
        'offer_id': result.offer_id,
        'ngo_id': result.ngo_id,
    }


@router.post('/api/admin/t3/retry/{donation_id}')
def t3_retry(
    donation_id: int,
    include_road: bool = Query(default=False, description='Optional bounded OSRM estimates'),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """Manually retry one DEMO donation after declines or offer timeouts.

    Admin only; disabled unless T3_DEMO_EXECUTION_ENABLED=true. No scheduler is
    installed here. Step 9 will decide how to make T3 the sole coordinator.
    """
    require_role(user, 'admin')
    if not _enabled():
        raise HTTPException(status_code=403, detail='T3 demo execution is disabled')
    if db.bind is None or db.bind.dialect.name != 'postgresql':
        raise HTTPException(status_code=503, detail='T3 execution requires PostgreSQL')
    if donation_id <= 0:
        raise HTTPException(status_code=404, detail='Donation not found')

    from ..agents.T3.recovery import reconcile_demo_offers

    try:
        recovery = reconcile_demo_offers(db, donation_id)
        if recovery.status == 'not_found':
            raise HTTPException(status_code=404, detail='Donation not found')
        if recovery.status == 'forbidden':
            raise HTTPException(status_code=403, detail='T3 retry is demo-only')
        if recovery.status != 'ready':
            return {
                'mode': 'controlled_demo_retry', 'recovery_status': recovery.status,
                'timed_out_offer_ids': list(recovery.timed_out_offer_ids),
                'decision': 'wait' if recovery.status == 'waiting' else 'none',
                'write_status': 'skipped', 'offer_created': False,
                'reason': recovery.reason,
            }

        # Reobserve *after* any pending-offer reconciliation. The planner
        # excludes ALL previously offered NGOs, including declines/timeouts.
        proposal = evaluate_donation(db, donation_id, include_road=include_road)
        if proposal.state.proposed_action != 'offer':
            return {
                'mode': 'controlled_demo_retry', 'recovery_status': 'ready',
                'timed_out_offer_ids': list(recovery.timed_out_offer_ids),
                'decision': proposal.state.proposed_action,
                'write_status': 'skipped', 'offer_created': False,
                'reason': '; '.join(proposal.state.reasons[-2:]),
            }
        result = execute_planned_offer(db, proposal, enable_writes=True)
        return {
            'mode': 'controlled_demo_retry', 'recovery_status': 'ready',
            'timed_out_offer_ids': list(recovery.timed_out_offer_ids),
            'decision': proposal.state.proposed_action,
            'write_status': result.status, 'offer_created': result.status == 'created',
            'offer_id': result.offer_id, 'ngo_id': result.ngo_id,
            'reason': result.reason,
        }
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail='T3 retry failed safely') from None

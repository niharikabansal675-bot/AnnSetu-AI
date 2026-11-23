"""Admin-only, read-only T3 preview with optional ML explanation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..agents.T3.graph import evaluate_donation
from ..database import db_session
from ..models import Donation, User
from ..security import current_user, require_role
from ..services.t3_explanations import build_decision_payload, get_explanation

router = APIRouter(tags=['T3 Agent (explanations)'])


@router.get('/api/admin/t3/explain/{donation_id}')
def explain_t3_decision(
    donation_id: int,
    include_road: bool = Query(default=False),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    require_role(user, 'admin')
    if donation_id < 1 or db.get(Donation, donation_id) is None:
        raise HTTPException(status_code=404, detail='Donation not found')
    try:
        result = evaluate_donation(db, donation_id, include_road=include_road)
    except ValueError:
        raise HTTPException(status_code=404, detail='Donation not found') from None
    except Exception:
        raise HTTPException(status_code=503, detail='T3 preview unavailable') from None
    # No DB commit, offer creation, or mutation here. The ML service only
    # receives IDs, quantity, and the already computed proposal.
    payload = build_decision_payload(result.state)
    explanation = get_explanation(payload)
    return {
        'mode': 'dry_run', 'writes_enabled': False, 'offer_created': False,
        'decision': payload, 'explanation': explanation,
        'nodes_visited': list(result.nodes_visited),
    }

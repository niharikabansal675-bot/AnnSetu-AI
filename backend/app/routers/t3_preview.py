from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import db_session
from ..models import Donation, User
from ..security import current_user, require_role
from ..agents.T3.graph import evaluate_donation

router = APIRouter(tags=['T3 Agent (preview)'])


@router.get('/api/admin/t3/preview/{donation_id}')
def t3_preview(
    donation_id: int,
    include_road: bool = Query(default=False, description='Optional bounded OSRM road estimates'),
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
):
    """Inspect a single donation and preview the agent's recommended decision.

    For admins only. No database writes, background scheduling or side effects.
    include_road=True may make up to five external OSRM lookups.
    """
    require_role(user, 'admin')
    if donation_id <= 0 or db.get(Donation, donation_id) is None:
        raise HTTPException(status_code=404, detail='Donation not found')

    try:
        result = evaluate_donation(db, donation_id, include_road=include_road)
    except ValueError:
        raise HTTPException(status_code=404, detail='Donation not found') from None
    except Exception:
        # Do not disclose internal data, stack traces, coordinates or credentials.
        raise HTTPException(status_code=503, detail='T3 preview could not be evaluated') from None

    output = result.as_dict()
    output['mode'] = 'dry_run'
    output['writes_enabled'] = False
    output['offer_created'] = False
    output['note'] = ('This is a proposed decision only. The existing coordinator '
                      'still handles live matching. An NGO must accept an offer.')
    return output

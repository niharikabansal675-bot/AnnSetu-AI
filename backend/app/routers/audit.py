from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

@router.get('/api/audit')
def audit(user:User=Depends(current_user),db:Session=Depends(db_session)):
    q=select(Audit).order_by(Audit.created_at.desc()).limit(100)
    rows=db.scalars(q).all()
    if user.role=='provider':
        ids=set(db.scalars(select(Donation.id).where(Donation.provider_id==user.id)).all());rows=[r for r in rows if r.donation_id in ids]
    elif user.role=='ngo':
        ids=set(db.scalars(select(Offer.donation_id).where(Offer.ngo_id==user.id)).all());rows=[r for r in rows if r.donation_id in ids]
    return [{'id':r.id,'donation_id':r.donation_id,'actor':r.actor,'action':r.action,'detail':r.detail,'created_at':aware(r.created_at).isoformat()} for r in rows]

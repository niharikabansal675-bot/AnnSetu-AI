from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

@router.get('/api/offers')
def list_offers(user:User=Depends(current_user),db:Session=Depends(db_session)):
    q=select(Offer).order_by(Offer.created_at.desc())
    if user.role=='ngo': q=q.where(Offer.ngo_id==user.id)
    elif user.role=='provider': q=q.join(Donation,Offer.donation_id==Donation.id).where(Donation.provider_id==user.id)
    offers=db.scalars(q).all()
    result=[]
    for o in offers:
        d=db.get(Donation,o.donation_id); NGO=db.get(User,o.ngo_id)
        result.append({'id':o.id,'donation_id':o.donation_id,'donation_title':d.title,'ngo_id':o.ngo_id,'ngo_name':NGO.organisation,'status':o.status,'reason':o.reason,'expires_at':aware(o.expires_at).isoformat()})
    return result

@router.post('/api/offers/{offer_id}/respond')
def respond(offer_id:int,body:OfferAction,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    # Obtain donation ID first, but do not trust any status read before locking.
    donation_id=db.scalar(select(Offer.donation_id).where(Offer.id==offer_id,Offer.ngo_id==user.id))
    if donation_id is None:
        raise HTTPException(404,'Offer not found')

    # Shared lock ordering with the legacy and T3 coordinators: donation first.
    # Protects against accepting an offer while another transaction is changing
    # donation availability or creating/reconciling an offer.
    d=db.scalar(select(Donation).where(Donation.id==donation_id).with_for_update())
    if d is None:
        raise HTTPException(404,'Donation not found')
    offer=db.scalar(select(Offer).where(Offer.id==offer_id,Offer.ngo_id==user.id).with_for_update())
    if offer is None:
        raise HTTPException(404,'Offer not found')
    db.refresh(d)
    db.refresh(offer)
    now=utcnow()
    if (offer.status!='pending' or aware(offer.expires_at)<=now
            or d.status!='available' or aware(d.deadline)<=now):
        raise HTTPException(409,'Offer is no longer active')

    # Enforce exact demo/real separation for BOTH accept and decline.
    # An NGO should not act on offers belonging to the other environment.
    if user.is_demo != d.is_demo:
        raise HTTPException(403,'NGO and donation must belong to the same environment')

    if body.decision=='accept':
        if not user.verified:
            raise HTTPException(403,'NGO is no longer verified')
        if user.capacity<d.quantity:
            raise HTTPException(409,'Insufficient NGO capacity')
        if aware(d.deadline)<=now+timedelta(minutes=30):
            raise HTTPException(409,'Collection deadline is too close')
        if d.accepted_ngo_id is not None:
            raise HTTPException(409,'Donation was already assigned')
        d.status='accepted'; d.accepted_ngo_id=user.id
        offer.status='accepted'
        for other in db.scalars(select(Offer).where(Offer.donation_id==d.id,Offer.id!=offer.id,Offer.status=='pending')).all():
            other.status='withdrawn'
        log(db,d.id,'ngo','offer_accepted',f'Accepted by {user.organisation}',user.id)
    else:
        offer.status='declined'
        log(db,d.id,'ngo','offer_declined',f'Declined by {user.organisation}',user.id)
    offer.responded_at=now
    db.commit()
    return {'message':'Response saved','status':offer.status}

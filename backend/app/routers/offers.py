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
    offer=db.get(Offer,offer_id)
    if not offer or offer.ngo_id!=user.id: raise HTTPException(404,'Offer not found')
    d=db.get(Donation,offer.donation_id)
    if offer.status!='pending' or aware(offer.expires_at)<=utcnow() or d.status!='available' or aware(d.deadline)<=utcnow(): raise HTTPException(409,'Offer is no longer active')
    if body.decision=='accept':
        if not user.verified or (not user.is_demo and d.is_demo): raise HTTPException(403,'NGO is not eligible to accept this donation')
        if user.capacity<d.quantity: raise HTTPException(409,'Insufficient NGO capacity')
        if aware(d.deadline)<=utcnow()+timedelta(minutes=30): raise HTTPException(409,'Collection deadline is too close')
        # Lock ensures exactly one accepted NGO in PostgreSQL; SQLite serialises writers for prototype.
        locked=db.scalar(select(Donation).where(Donation.id==d.id).with_for_update())
        if locked.status!='available': raise HTTPException(409,'Already accepted')
        locked.status='accepted'; locked.accepted_ngo_id=user.id
        offer.status='accepted'
        for other in db.scalars(select(Offer).where(Offer.donation_id==d.id,Offer.id!=offer.id,Offer.status=='pending')).all(): other.status='withdrawn'
        log(db,d.id,'ngo','offer_accepted',f'Accepted by {user.organisation}',user.id)
    else:
        offer.status='declined'; log(db,d.id,'ngo','offer_declined',f'Declined by {user.organisation}',user.id)
    offer.responded_at=utcnow();db.commit()
    return {'message':'Response saved','status':offer.status}

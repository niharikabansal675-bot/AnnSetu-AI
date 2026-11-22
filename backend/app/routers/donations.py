from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

@router.get('/api/donations')
def donations(user:User=Depends(current_user),db:Session=Depends(db_session)):
    all_rows=db.scalars(select(Donation).order_by(Donation.created_at.desc())).all()
    for d in all_rows: expire_if_needed(db,d)
    if user.role=='provider': all_rows=[d for d in all_rows if d.provider_id==user.id]
    if user.role=='ngo':
        # NGOs see only offers sent to them, their accepted donations, and available demo listings for exploration.
        offered=set(db.scalars(select(Offer.donation_id).where(Offer.ngo_id==user.id)).all())
        all_rows=[d for d in all_rows if d.id in offered or d.accepted_ngo_id==user.id or (d.is_demo and d.status=='available')]
    return [serial_donation(d,db) for d in all_rows]

@router.post('/api/donations',status_code=201)
def create_donation(body:DonationIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'provider')
    if not user.verified: raise HTTPException(403,'Admin must verify your provider account first')
    if aware(body.deadline) <= utcnow(): raise HTTPException(400,'Pickup deadline must be in the future')
    if aware(body.prepared_at)>utcnow()+timedelta(minutes=5): raise HTTPException(400,'Food must already be prepared and confirmed available')
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(422,'Supply both latitude and longitude, or neither')
    if body.latitude is not None:ensure_postgis(db)
    donation=Donation(provider_id=user.id,title=body.title,food_type=body.food_type,quantity=body.quantity,locality=body.locality,address=body.address,prepared_at=aware(body.prepared_at),storage=body.storage,deadline=aware(body.deadline),status='available',is_demo=user.is_demo)
    db.add(donation);db.flush()
    if body.latitude is not None:
        set_pickup_point(db,donation.id,body.latitude,body.longitude)
    log(db,donation.id,'provider','listing_created','Confirmed food listing created',user.id);db.commit(); db.refresh(donation)
    return serial_donation(donation,db)

@router.patch('/api/donations/{donation_id}')
def update_donation(donation_id:int, body:DonationUpdateIn, user:User=Depends(current_user), db:Session=Depends(db_session)):
    require_role(user,'provider')
    d=db.get(Donation,donation_id)
    if not d or d.provider_id!=user.id: raise HTTPException(404,'Donation not found')
    if d.status!='available': raise HTTPException(409,'Only available listings can be edited')
    if db.scalar(select(Offer.id).where(Offer.donation_id==d.id,Offer.status=='pending')):
        raise HTTPException(409,'Wait until the active offer resolves before editing')
    if aware(body.deadline)<=utcnow(): raise HTTPException(400,'Deadline must be in the future')
    d.title=body.title; d.quantity=body.quantity; d.storage=body.storage; d.deadline=aware(body.deadline)
    log(db,d.id,'provider','listing_edited','Food listing updated',user.id)
    db.commit();return serial_donation(d,db)

@router.post('/api/donations/{donation_id}/cancel')
def cancel_donation(donation_id:int, body:CancelIn, user:User=Depends(current_user), db:Session=Depends(db_session)):
    require_role(user,'provider','admin')
    d=db.get(Donation,donation_id)
    if not d or (user.role=='provider' and d.provider_id!=user.id): raise HTTPException(404,'Donation not found')
    if d.status in ('completed','cancelled','expired','picked_up'):
        raise HTTPException(409,'Cannot cancel this donation at its current stage')
    d.status='cancelled'
    for offer in db.scalars(select(Offer).where(Offer.donation_id==d.id,Offer.status=='pending')).all(): offer.status='withdrawn'
    log(db,d.id,user.role,'listing_cancelled',body.reason,user.id)
    db.commit();return {'status':'cancelled','message':'Donation cancelled'}

@router.get('/api/donations/{donation_id}/tracking')
def donation_tracking(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    d=db.get(Donation,donation_id)
    if not d: raise HTTPException(404,'Donation not found')
    can_view=user.role=='admin' or (user.role=='provider' and d.provider_id==user.id) or (user.role=='ngo' and (d.accepted_ngo_id==user.id or db.scalar(select(Offer.id).where(Offer.donation_id==d.id,Offer.ngo_id==user.id)) is not None))
    if not can_view: raise HTTPException(403,'Not authorised to view tracking')
    events=db.scalars(select(Audit).where(Audit.donation_id==d.id).order_by(Audit.created_at)).all()
    return {'donation':serial_donation(d,db),'events':[{'action':e.action,'actor':e.actor,'detail':e.detail,'created_at':aware(e.created_at).isoformat()} for e in events]}

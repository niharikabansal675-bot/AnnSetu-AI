from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

def tracking_access(d: Donation, user: User):
    if user.role == 'admin': return
    if user.role == 'provider' and d.provider_id == user.id: return
    if user.role == 'ngo' and d.accepted_ngo_id == user.id: return
    raise HTTPException(404, 'Donation not found')

@router.get('/api/donations/{donation_id}/live')
def get_live_position(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    d=db.get(Donation,donation_id)
    if not d:raise HTTPException(404,'Donation not found')
    tracking_access(d,user)
    t=db.get(CollectorTracking, donation_id)
    active=bool(t and t.sharing and d.status == 'picked_up')
    updated=aware(t.updated_at) if t and t.updated_at else None
    fresh=bool(active and updated and (utcnow()-updated).total_seconds() <= 120)
    # Browser tabs can be suspended or closed without running cleanup.
    # Auto-expire sessions without an update, so a stale device never remains 'live'.
    if active and updated and not fresh:
        t.sharing=False;t.latitude=None;t.longitude=None;t.accuracy_m=None;t.updated_at=None
        db.commit()
        active=False
        updated=None
    return {'sharing':active,'fresh':fresh,
      'position':{'latitude':t.latitude,'longitude':t.longitude,'accuracy_m':t.accuracy_m} if fresh and t.latitude is not None and t.longitude is not None else None,
      'updated_at':updated.isoformat() if active and updated else None,
      'collector_id':t.collector_id if active and t else None}

@router.post('/api/donations/{donation_id}/live/start')
def start_live_position(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    d=db.get(Donation,donation_id)
    if not d or d.accepted_ngo_id!=user.id: raise HTTPException(404,'Donation not assigned')
    if not user.verified:raise HTTPException(403,'NGO is not verified')
    if d.status!='picked_up':raise HTTPException(409,'Live sharing requires confirmed pickup')
    t=db.get(CollectorTracking,donation_id)
    if t is None:
        t=CollectorTracking(donation_id=donation_id,collector_id=user.id)
        db.add(t)
    t.collector_id=user.id;t.sharing=True
    t.latitude=None;t.longitude=None;t.accuracy_m=None;t.updated_at=None
    log(db,d.id,'ngo','location_sharing_started','Collector enabled voluntary delivery location sharing',user.id)
    db.commit()
    return {'message':'Location sharing enabled. Keep this page open while delivering.'}

@router.post('/api/donations/{donation_id}/live/update')
def update_live_position(donation_id:int,body:LivePointIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    d=db.get(Donation,donation_id)
    if not d or d.accepted_ngo_id!=user.id:raise HTTPException(404,'Donation not assigned')
    t=db.get(CollectorTracking,donation_id)
    if d.status!='picked_up' or not t or not t.sharing or t.collector_id!=user.id:
        raise HTTPException(409,'Location sharing is not active')
    t.latitude=round(body.latitude,6);t.longitude=round(body.longitude,6)
    t.accuracy_m=round(body.accuracy_m,1);t.updated_at=utcnow()
    db.commit()
    return {'message':'Location updated','updated_at':t.updated_at.isoformat()}

@router.post('/api/donations/{donation_id}/live/stop')
def stop_live_position(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    d=db.get(Donation,donation_id)
    if not d or d.accepted_ngo_id!=user.id:raise HTTPException(404,'Donation not assigned')
    t=db.get(CollectorTracking,donation_id)
    if t and t.collector_id==user.id:
        t.sharing=False;t.latitude=None;t.longitude=None;t.accuracy_m=None;t.updated_at=None
        log(db,d.id,'ngo','location_sharing_stopped','Collector disabled delivery location sharing',user.id)
        db.commit()
    return {'message':'Location sharing stopped and last position cleared'}

@router.get('/api/donations/{donation_id}/delivery-receipt')
def delivery_receipt(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    d=db.get(Donation,donation_id)
    if not d:raise HTTPException(404,'Donation not found')
    tracking_access(d,user)
    r=db.get(DeliveryReceipt,donation_id)
    return {'receipt':{'receiver_name':r.receiver_name,'received_quantity':r.received_quantity,
      'condition':r.condition,'notes':r.notes,'confirmed_at':aware(r.confirmed_at).isoformat(),
      'confirmed_by_user_id':r.confirmed_by} if r else None}

@router.post('/api/donations/{donation_id}/delivery-confirm')
def confirm_delivery(donation_id:int,body:DeliveryConfirmIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    d=db.get(Donation,donation_id)
    if not d or d.accepted_ngo_id!=user.id:raise HTTPException(404,'Donation not assigned')
    if d.status!='picked_up':raise HTTPException(409,'Pickup must be verified first')
    if not body.confirmed_received:raise HTTPException(422,'Receipt confirmation is required')
    if body.received_quantity>d.quantity:raise HTTPException(422,'Received quantity cannot exceed donated quantity')
    if body.condition=='rejected':raise HTTPException(409,'Rejected food must be escalated to an admin; do not mark completed')
    if db.get(DeliveryReceipt,donation_id):raise HTTPException(409,'Receipt already exists')
    receipt=DeliveryReceipt(donation_id=d.id,confirmed_by=user.id,receiver_name=body.receiver_name.strip(),
      received_quantity=body.received_quantity,condition=body.condition,notes=body.notes.strip())
    db.add(receipt)
    d.status='completed'
    t=db.get(CollectorTracking,donation_id)
    if t:
        t.sharing=False;t.latitude=None;t.longitude=None;t.accuracy_m=None;t.updated_at=None
    log(db,d.id,'ngo','delivery_confirmed',
      f'Receipt attested by {body.receiver_name.strip()}: {body.received_quantity}/{d.quantity} meals; condition {body.condition}. Not independently verified.',user.id)
    db.commit()
    return {'message':'Delivery receipt recorded; location sharing stopped','status':'completed'}

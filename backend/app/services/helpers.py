from __future__ import annotations
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import routing  # ensures routing module is importable
from ..models import User, Donation, Audit
from ..security import utcnow, aware

def serial_user(u):
    return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'organisation':u.organisation,'locality':u.locality,'capacity':u.capacity,'verified':u.verified,'is_demo':u.is_demo}

def serial_donation(d, db):
    provider = db.get(User, d.provider_id)
    ngo = db.get(User, d.accepted_ngo_id) if d.accepted_ngo_id else None
    return {'id':d.id,'title':d.title,'food_type':d.food_type,'quantity':d.quantity,'locality':d.locality,'address':d.address,'prepared_at':aware(d.prepared_at).isoformat(),'storage':d.storage,'deadline':aware(d.deadline).isoformat(),'status':d.status,'provider_id':d.provider_id,'provider_name':provider.organisation if provider else '', 'accepted_ngo_id':d.accepted_ngo_id,'accepted_ngo_name':ngo.organisation if ngo else None,'is_demo':d.is_demo,'created_at':aware(d.created_at).isoformat()}

def log(db, donation_id, actor, action, detail, actor_id=None):
    db.add(Audit(donation_id=donation_id,actor=actor,actor_id=actor_id,action=action,detail=detail))

def expire_if_needed(db, donation):
    if donation.status == 'available' and aware(donation.deadline) <= utcnow():
        donation.status='expired'; log(db, donation.id, 'system','expired','Pickup deadline passed'); db.commit()

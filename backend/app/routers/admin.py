from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

@router.get('/api/admin/users')
def admin_users(user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin');return [serial_user(u) for u in db.scalars(select(User).order_by(User.id.desc())).all()]

@router.patch('/api/admin/users/{user_id}/verify')
def verify_user(user_id:int,body:VerifyIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin');target=db.get(User,user_id)
    if not target or target.role=='admin':raise HTTPException(404,'Account not found')
    target.verified=body.verified;log(db,None,'admin','account_verified' if body.verified else 'verification_revoked',f'User {user_id}',user.id);db.commit()
    return serial_user(target)

@router.get('/api/reports')
def reports(user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin')
    donations=db.scalars(select(Donation)).all()
    offers=db.scalars(select(Offer)).all()
    audit=db.scalars(select(Audit)).all()
    status_counts={s:sum(d.status==s for d in donations) for s in ('available','accepted','picked_up','completed','cancelled','expired')}
    return {'donations_by_status':status_counts,'total_donations':len(donations),
            'completed_quantity':sum(d.quantity for d in donations if d.status=='completed'),
            'offer_responses':{'accepted':sum(o.status=='accepted' for o in offers),'declined':sum(o.status=='declined' for o in offers),'timed_out':sum(o.status=='timed_out' for o in offers)},
            'agent_actions':sum(a.actor=='agent' for a in audit),'escalations':sum(a.action=='escalation' for a in audit),
            'disclaimer':'These are application records, not demonstrated hunger-reduction outcomes.'}

@router.get('/api/stats')
def stats(user:User=Depends(current_user),db:Session=Depends(db_session)):
    rows=db.scalars(select(Donation)).all()
    if user.role=='provider':rows=[d for d in rows if d.provider_id==user.id]
    if user.role=='ngo':rows=[d for d in rows if d.accepted_ngo_id==user.id or d.id in set(db.scalars(select(Offer.donation_id).where(Offer.ngo_id==user.id)).all())]
    return {'total':len(rows),'available':sum(d.status=='available' for d in rows),'active':sum(d.status in ('accepted','picked_up') for d in rows),'completed':sum(d.status=='completed' for d in rows),'meals':sum(d.quantity for d in rows if d.status=='completed')}

@router.post('/api/demo/seed')
def seed_demo(user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin')
    if db.scalar(select(User.id).where(User.is_demo.is_(True))):raise HTTPException(409,'Demo data already exists')
    ngos=[('Hope Community Kitchen','Indirapuram',150),('City Relief Network','Vaishali',80),('Nourish Together','Raj Nagar',250),('Neighbourhood Meals','Crossings Republik',100)]
    for name,area,capacity in ngos:
        u=User(name=name,email=f'demo-ngo-{uuid4().hex[:8]}@example.invalid',password_hash=password_hash(secrets.token_urlsafe(20)),role='ngo',organisation=name,locality=area,capacity=capacity,verified=True,is_demo=True);db.add(u)
    p=User(name='Demo Provider',email=f'demo-provider-{uuid4().hex[:8]}@example.invalid',password_hash=password_hash(secrets.token_urlsafe(20)),role='provider',organisation='Sample Banquet',locality='Indirapuram',verified=True,is_demo=True)
    db.add(p);db.flush()
    for title,qty,area in [('Fresh packed vegetarian meals',75,'Indirapuram'),('Catered dal and rice',50,'Vaishali'),('Prepared banquet meals',90,'Raj Nagar')]:
        d=Donation(provider_id=p.id,title=title,food_type='Vegetarian meals',quantity=qty,locality=area,address=f'DEMO ONLY — {area}, Ghaziabad',prepared_at=utcnow()-timedelta(minutes=20),storage='Sample: covered, temperature monitored',deadline=utcnow()+timedelta(hours=3),is_demo=True)
        db.add(d);db.flush();log(db,d.id,'system','demo_created','Synthetic demonstration record; not a real donation')
    db.commit();return {'message':'Simulation records added. These NGOs and donations are fictional.'}

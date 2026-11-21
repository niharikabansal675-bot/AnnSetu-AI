"""Food Rescue — secure role-based prototype API.

Real NGO organisations must enrol and be approved before receiving real donations.
Sample NGOs are simulation-only; no real food pickup should be arranged from demo data.
"""
from __future__ import annotations
import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import hashlib
import hmac
import os
import secrets
from typing import Literal
import json
from urllib import request as urlrequest
from pathlib import Path
from uuid import uuid4

import jwt
import qrcode
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

# Load the environment from the backend directory, regardless of shell working directory.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./foodrescue.db')
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-change-me')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(130))
    email: Mapped[str] = mapped_column(String(250), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(350))
    role: Mapped[str] = mapped_column(String(20))
    organisation: Mapped[str] = mapped_column(String(180), default='')
    locality: Mapped[str] = mapped_column(String(100), default='Ghaziabad')
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Donation(Base):
    __tablename__ = 'donations'
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(150))
    food_type: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer)
    locality: Mapped[str] = mapped_column(String(90))
    address: Mapped[str] = mapped_column(String(300))
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    storage: Mapped[str] = mapped_column(String(160))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(25), default='available')
    accepted_ngo_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    qr_token: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: secrets.token_urlsafe(36))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Offer(Base):
    __tablename__ = 'offers'
    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int] = mapped_column(ForeignKey('donations.id'))
    ngo_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    reason: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int | None] = mapped_column(ForeignKey('donations.id'), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    actor: Mapped[str] = mapped_column(String(35))
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=130)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal['provider','ngo']
    organisation: str = Field(min_length=2, max_length=180)
    locality: str = Field(min_length=2, max_length=100)
    capacity: int = Field(default=0, ge=0, le=100000)

class CoordinatesIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class DonationIn(BaseModel):
    title: str = Field(min_length=4, max_length=150)
    food_type: str = Field(min_length=2, max_length=80)
    quantity: int = Field(gt=0, le=100000)
    locality: str = Field(min_length=2, max_length=90)
    address: str = Field(min_length=5, max_length=300)
    prepared_at: datetime
    storage: str = Field(min_length=4, max_length=160)
    deadline: datetime
    # Optional until the map picker is added to the React donation form.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

class ScanIn(BaseModel):
    token: str

class VerifyIn(BaseModel):
    verified: bool

class CancelIn(BaseModel):
    reason: str = Field(min_length=5, max_length=300)

class DonationUpdateIn(BaseModel):
    title: str = Field(min_length=4, max_length=150)
    quantity: int = Field(gt=0, le=100000)
    storage: str = Field(min_length=4, max_length=160)
    deadline: datetime

class OfferAction(BaseModel):
    decision: Literal['accept','decline']

def utcnow(): return datetime.now(timezone.utc)
def aware(d): return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
def password_hash(password):
    salt = secrets.token_bytes(16)
    hash_value = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ':' + hash_value.hex()
def check_password(password, stored):
    try:
        salt_hex, target = stored.split(':', 1)
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(target))
    except Exception: return False

def token_for(u):
    return jwt.encode({'sub': str(u.id), 'exp': utcnow() + timedelta(days=2)}, JWT_SECRET, algorithm='HS256')

def db_session():
    with SessionLocal() as db: yield db

from fastapi import Header

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(db_session)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401, 'Please sign in')
    try: user_id = int(jwt.decode(authorization[7:], JWT_SECRET, algorithms=['HS256'])['sub'])
    except Exception: raise HTTPException(401, 'Session expired or invalid')
    user = db.get(User, user_id)
    if not user: raise HTTPException(401, 'Account not found')
    return user

def require_role(user, *roles):
    if user.role not in roles: raise HTTPException(403, 'Not allowed for this account')

def serial_user(u):
    return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'organisation':u.organisation,'locality':u.locality,'capacity':u.capacity,'verified':u.verified,'is_demo':u.is_demo}

def serial_donation(d, db):
    provider = db.get(User, d.provider_id)
    ngo = db.get(User, d.accepted_ngo_id) if d.accepted_ngo_id else None
    return {'id':d.id,'title':d.title,'food_type':d.food_type,'quantity':d.quantity,'locality':d.locality,'address':d.address,'prepared_at':aware(d.prepared_at).isoformat(),'storage':d.storage,'deadline':aware(d.deadline).isoformat(),'status':d.status,'provider_id':d.provider_id,'provider_name':provider.organisation if provider else '', 'accepted_ngo_id':d.accepted_ngo_id,'accepted_ngo_name':ngo.organisation if ngo else None,'is_demo':d.is_demo,'created_at':aware(d.created_at).isoformat()}

def log(db, donation_id, actor, action, detail, actor_id=None):
    db.add(Audit(donation_id=donation_id,actor=actor,actor_id=actor_id,action=action,detail=detail))

# GIS is stored in PostGIS geography columns added through pgAdmin.
# Explicit SQL avoids requiring geoalchemy2 and does not remap existing ORM models.
GIS_RADIUS_KM = float(os.getenv('GIS_MATCH_RADIUS_KM', '20'))
if not 0 < GIS_RADIUS_KM <= 100:
    raise ValueError('GIS_MATCH_RADIUS_KM must be between 0 and 100')

def ensure_postgis(db: Session):
    if db.bind.dialect.name != 'postgresql':
        raise HTTPException(503, 'GIS requires the configured PostgreSQL/PostGIS database; check backend/.env')
    installed = db.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')"))
    if not installed:
        raise HTTPException(503, 'PostGIS extension is not enabled in the application database')

def set_user_point(db: Session, user_id: int, latitude: float, longitude: float):
    db.execute(text('''UPDATE users
        SET location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        WHERE id = :id'''), {'id':user_id, 'lat':latitude, 'lon':longitude})

def set_pickup_point(db: Session, donation_id: int, latitude: float, longitude: float):
    db.execute(text('''UPDATE donations
        SET pickup_location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        WHERE id = :id'''), {'id':donation_id, 'lat':latitude, 'lon':longitude})

def point_coordinates(db: Session, table: str, column: str, record_id: int):
    # table/column come exclusively from this source file, never from user input.
    result = db.execute(text(f'''SELECT ST_Y({column}::geometry) AS latitude,
        ST_X({column}::geometry) AS longitude FROM {table} WHERE id=:id'''),
        {'id':record_id}).mappings().first()
    if not result or result['latitude'] is None:
        return None
    return {'latitude':float(result['latitude']), 'longitude':float(result['longitude'])}

def expire_if_needed(db, donation):
    if donation.status == 'available' and aware(donation.deadline) <= utcnow():
        donation.status='expired'; log(db, donation.id, 'system','expired','Pickup deadline passed'); db.commit()

app = FastAPI(title='Food Rescue API', version='0.1.0', description='Ghaziabad food rescue coordination API')
# Explicit, exact browser origins. Never use '*' with credentialed requests.
DEFAULT_CORS_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173'
CORS_ORIGINS = [origin.strip().rstrip('/') for origin in os.getenv('CORS_ORIGINS', DEFAULT_CORS_ORIGINS).split(',') if origin.strip()]
# Keep a safe development fallback even when an old .env lists only port 5173.
for local_origin in ('http://localhost:3000', 'http://127.0.0.1:3000'):
    if local_origin not in CORS_ORIGINS:
        CORS_ORIGINS.append(local_origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type', 'Accept'],
)

@app.on_event('startup')
def startup(): Base.metadata.create_all(engine)

@app.get('/api/health')
def health(): return {'status':'ok','service':'food-rescue-api'}

@app.post('/api/auth/register', status_code=201)
def register(body: RegisterIn, db: Session=Depends(db_session)):
    if db.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,'Email already registered')
    user=User(name=body.name,email=body.email.lower(),password_hash=password_hash(body.password),role=body.role,organisation=body.organisation,locality=body.locality,capacity=body.capacity,verified=False)
    db.add(user); db.commit(); db.refresh(user)
    return {'token':token_for(user),'user':serial_user(user)}

@app.post('/api/auth/login')
def login(body: LoginIn,db:Session=Depends(db_session)):
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not check_password(body.password,user.password_hash): raise HTTPException(401,'Invalid email or password')
    return {'token':token_for(user),'user':serial_user(user)}

@app.get('/api/me')
def get_me(user:User=Depends(current_user)): return serial_user(user)

@app.get('/api/gis/health')
def gis_health(user:User=Depends(current_user), db:Session=Depends(db_session)):
    ensure_postgis(db)
    return {'status':'ok','postgis_version':db.scalar(text('SELECT PostGIS_Version()')),
            'match_radius_km':GIS_RADIUS_KM}

@app.put('/api/me/location')
def update_my_location(body:CoordinatesIn, user:User=Depends(current_user), db:Session=Depends(db_session)):
    require_role(user,'ngo','provider')
    ensure_postgis(db)
    set_user_point(db,user.id,body.latitude,body.longitude)
    log(db,None,user.role,'location_updated','Organisation location updated by account holder',user.id)
    db.commit()
    return {'message':'Organisation location saved','latitude':body.latitude,'longitude':body.longitude}

@app.get('/api/me/location')
def get_my_location(user:User=Depends(current_user),db:Session=Depends(db_session)):
    ensure_postgis(db)
    return {'location':point_coordinates(db,'users','location',user.id)}

@app.put('/api/donations/{donation_id}/location')
def update_pickup_location(donation_id:int,body:CoordinatesIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'provider')
    d=db.get(Donation,donation_id)
    if not d or d.provider_id!=user.id:raise HTTPException(404,'Donation not found')
    if d.status!='available':raise HTTPException(409,'Pickup location can only be edited while available')
    if db.scalar(select(Offer.id).where(Offer.donation_id==d.id,Offer.status=='pending')):
        raise HTTPException(409,'Wait until the active offer resolves before editing the pickup location')
    ensure_postgis(db)
    set_pickup_point(db,d.id,body.latitude,body.longitude)
    log(db,d.id,'provider','pickup_location_updated','Pickup coordinates updated by provider',user.id)
    db.commit()
    return {'message':'Pickup location saved','latitude':body.latitude,'longitude':body.longitude}

@app.get('/api/donations/{donation_id}/geo')
def donation_geo(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    d=db.get(Donation,donation_id)
    if not d:raise HTTPException(404,'Donation not found')
    offered_to_ngo=(user.role=='ngo' and db.scalar(select(Offer.id).where(
        Offer.donation_id==d.id,Offer.ngo_id==user.id)) is not None)
    authorised=(user.role=='admin' or (user.role=='provider' and d.provider_id==user.id)
        or (user.role=='ngo' and (d.accepted_ngo_id==user.id or offered_to_ngo)))
    if not authorised:raise HTTPException(403,'Not authorised to view this donation location')
    ensure_postgis(db)
    pickup=point_coordinates(db,'donations','pickup_location',d.id)
    # Receiving NGO coordinates are only exposed to the provider after acceptance.
    destination=None
    if d.accepted_ngo_id and (user.role=='admin' or
            (user.role=='provider' and d.provider_id==user.id) or
            (user.role=='ngo' and d.accepted_ngo_id==user.id)):
        destination=point_coordinates(db,'users','location',d.accepted_ngo_id)
    distance_km=None
    if pickup and destination:
        distance_m=db.scalar(text('''SELECT ST_Distance(d.pickup_location,u.location)
            FROM donations d JOIN users u ON u.id=d.accepted_ngo_id
            WHERE d.id=:id'''),{'id':d.id})
        if distance_m is not None:distance_km=round(float(distance_m)/1000,2)
    return {'donation_id':d.id,'pickup':pickup,'destination':destination,
            'straight_line_distance_km':distance_km,'route_distance_km':None,
            'note':'GIS distance is straight-line only; no GPS tracking or road routing is enabled yet.'}

@app.get('/api/donations')
def donations(user:User=Depends(current_user),db:Session=Depends(db_session)):
    all_rows=db.scalars(select(Donation).order_by(Donation.created_at.desc())).all()
    for d in all_rows: expire_if_needed(db,d)
    if user.role=='provider': all_rows=[d for d in all_rows if d.provider_id==user.id]
    if user.role=='ngo':
        # NGOs see only offers sent to them, their accepted donations, and available demo listings for exploration.
        offered=set(db.scalars(select(Offer.donation_id).where(Offer.ngo_id==user.id)).all())
        all_rows=[d for d in all_rows if d.id in offered or d.accepted_ngo_id==user.id or (d.is_demo and d.status=='available')]
    return [serial_donation(d,db) for d in all_rows]

@app.post('/api/donations',status_code=201)
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

@app.patch('/api/donations/{donation_id}')
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

@app.post('/api/donations/{donation_id}/cancel')
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

@app.get('/api/donations/{donation_id}/tracking')
def donation_tracking(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    d=db.get(Donation,donation_id)
    if not d: raise HTTPException(404,'Donation not found')
    can_view=user.role=='admin' or (user.role=='provider' and d.provider_id==user.id) or (user.role=='ngo' and (d.accepted_ngo_id==user.id or db.scalar(select(Offer.id).where(Offer.donation_id==d.id,Offer.ngo_id==user.id)) is not None))
    if not can_view: raise HTTPException(403,'Not authorised to view tracking')
    events=db.scalars(select(Audit).where(Audit.donation_id==d.id).order_by(Audit.created_at)).all()
    return {'donation':serial_donation(d,db),'events':[{'action':e.action,'actor':e.actor,'detail':e.detail,'created_at':aware(e.created_at).isoformat()} for e in events]}

@app.get('/api/offers')
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

@app.post('/api/offers/{offer_id}/respond')
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

# The controlled coordinator is a real observe -> evaluate -> act -> verify workflow.
# It does NOT purport to be an LLM. Optional LLM reasoning can be added once the workflow is tested.
LOCALITIES = {'indirapuram':(28.642,77.370),'vaishali':(28.649,77.340),'vasundhara':(28.660,77.370),'raj nagar':(28.688,77.448),'raj nagar extension':(28.706,77.435),'crossings republik':(28.630,77.435),'kaushambi':(28.646,77.324),'sahibabad':(28.676,77.357),'govindpuram':(28.680,77.478),'ghaziabad':(28.670,77.430)}

def locality_distance(a,b):
    # Approximate distances ONLY for simulated demo rankings; never a travel-time guarantee.
    from math import radians,sin,cos,asin,sqrt
    c1=LOCALITIES.get(a.lower().strip());c2=LOCALITIES.get(b.lower().strip())
    if not c1 or not c2: return None
    lat1,lon1=map(radians,c1);lat2,lon2=map(radians,c2)
    delta=2*6371*asin(sqrt(sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2))
    return round(delta,1)

@app.post('/api/agent/run')
def run_coordinator(user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin','provider')
    rows=db.scalars(select(Donation).where(Donation.status=='available').order_by(Donation.created_at.asc())).all()
    if user.role=='provider': rows=[d for d in rows if d.provider_id==user.id]
    created=[]; escalated=[]; skipped=[]
    for d in rows:
        expire_if_needed(db,d)
        if d.status!='available': continue
        # Observe: check outstanding offer; expire timeouts
        pending=db.scalars(select(Offer).where(Offer.donation_id==d.id,Offer.status=='pending')).all()
        for o in pending:
            if aware(o.expires_at)<=utcnow(): o.status='timed_out';log(db,d.id,'agent','offer_timed_out',f'Offer {o.id} expired')
        db.flush()
        still_pending=[o for o in pending if o.status=='pending']
        if still_pending: skipped.append({'donation_id':d.id,'reason':'Pending offer is still active'});continue
        already_offered=set(db.scalars(select(Offer.ngo_id).where(Offer.donation_id==d.id)).all())
        ngo_rows=db.scalars(select(User).where(User.role=='ngo',User.verified.is_(True),User.capacity>=d.quantity)).all()
        eligible=[]
        # Real donations: accurate PostGIS coordinate matching ONLY.
        # Demo donations without coordinates retain their clearly labelled approximate fallback.
        ensure_postgis(db)
        pickup_exists=db.scalar(text('SELECT pickup_location IS NOT NULL FROM donations WHERE id=:id'),{'id':d.id})
        gis_distances={}
        if pickup_exists:
            locations=db.execute(text('''SELECT u.id AS ngo_id,
                    ST_Distance(u.location,d.pickup_location)/1000.0 AS km
                FROM users u CROSS JOIN donations d
                WHERE d.id=:donation_id AND u.role='ngo' AND u.verified = TRUE
                    AND u.capacity >= d.quantity AND u.is_demo = d.is_demo
                    AND u.location IS NOT NULL
                    AND ST_DWithin(u.location,d.pickup_location,:radius_m)'''),
                {'donation_id':d.id,'radius_m':GIS_RADIUS_KM*1000}).mappings().all()
            gis_distances={row['ngo_id']:round(float(row['km']),2) for row in locations}
        for ngo in ngo_rows:
            if ngo.id in already_offered or ngo.is_demo!=d.is_demo: continue
            if aware(d.deadline) <= utcnow()+timedelta(minutes=30):continue
            # Never infer a real NGO's position from its locality name.
            if pickup_exists:
                dist=gis_distances.get(ngo.id)
                method='PostGIS straight-line'
            elif d.is_demo:
                dist=locality_distance(d.locality,ngo.locality)
                method='SIMULATION locality approximation'
            else:
                dist=None
                method='not available'
            if dist is None: continue
            eligible.append((dist,-ngo.capacity,ngo,method))
        eligible.sort(key=lambda x:(x[0],x[1],x[2].id))
        if not eligible:
            log(db,d.id,'agent','escalation','No eligible NGO with confirmed location (real donations), matching capacity, verification and deadline; check GIS coordinates or radius')
            escalated.append(d.id); continue
        distance,_,ngo,distance_method=eligible[0]
        # Optional LLM assists selection only within the backend-approved shortlist.
        # It never receives identities, addresses, credentials or unrestricted tools.
        ai_note='Deterministic coordination policy'
        if os.getenv('OPENAI_API_KEY') and os.getenv('ENABLE_LLM_RANKING','false').lower()=='true':
            try:
                candidates=[{'candidate':str(n.id),'distance_km':distance_km,'capacity':n.capacity} for distance_km,_,n,_ in eligible[:5]]
                req_data={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'), 'temperature':0,
                          'messages':[{'role':'system','content':'Select a candidate from the provided eligible list ONLY. Return JSON object with keys candidate and rationale. Minimise distance; use capacity as a tiebreaker. Never invent a candidate or loosen constraints.'},
                                      {'role':'user','content':json.dumps({'quantity':d.quantity,'candidates':candidates})}],
                          'response_format':{'type':'json_object'}}
                req=urlrequest.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(req_data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},method='POST')
                with urlrequest.urlopen(req,timeout=8) as reply: response_data=json.load(reply)
                answer=json.loads(response_data['choices'][0]['message']['content'])
                chosen=next((e for e in eligible if str(e[2].id)==str(answer.get('candidate'))),None)
                if chosen:
                    distance,_,ngo,distance_method=chosen
                    ai_note='LLM-selected from verified shortlist; '+str(answer.get('rationale',''))[:180]
                else: ai_note='LLM returned non-eligible candidate; deterministic fallback'
            except Exception as exc:
                ai_note='LLM unavailable; deterministic fallback: '+type(exc).__name__
        reason=f'Verified; capacity {ngo.capacity} ≥ quantity {d.quantity}; {distance_method} distance {distance} km; not road travel time; deadline policy valid. NGO makes final choice. {ai_note}.'
        offer=Offer(donation_id=d.id,ngo_id=ngo.id,status='pending',reason=reason,expires_at=min(utcnow()+timedelta(minutes=15),aware(d.deadline)))
        db.add(offer);db.flush()
        log(db,d.id,'agent','offer_created',f'Offer {offer.id} to {ngo.organisation}. {reason}')
        created.append({'donation_id':d.id,'ngo':ngo.organisation,'offer_id':offer.id,'reason':reason})
    db.commit()
    return {'created':created,'escalated':escalated,'skipped':skipped,'note':'Rule-governed coordination. Optional bounded LLM ranking only when explicitly enabled; deterministic fallback otherwise.'}

@app.get('/api/audit')
def audit(user:User=Depends(current_user),db:Session=Depends(db_session)):
    q=select(Audit).order_by(Audit.created_at.desc()).limit(100)
    rows=db.scalars(q).all()
    if user.role=='provider':
        ids=set(db.scalars(select(Donation.id).where(Donation.provider_id==user.id)).all());rows=[r for r in rows if r.donation_id in ids]
    elif user.role=='ngo':
        ids=set(db.scalars(select(Offer.donation_id).where(Offer.ngo_id==user.id)).all());rows=[r for r in rows if r.donation_id in ids]
    return [{'id':r.id,'donation_id':r.donation_id,'actor':r.actor,'action':r.action,'detail':r.detail,'created_at':aware(r.created_at).isoformat()} for r in rows]


@app.get('/api/donations/{donation_id}/qr')
def donation_qr(
    donation_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(db_session)
):
    d = db.get(Donation, donation_id)

    # Check whether donation exists
    if not d:
        raise HTTPException(
            status_code=404,
            detail="Donation not found"
        )

    # Only the provider who created the donation
    # can view its pickup QR code
    if user.role != "provider" or d.provider_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the donation provider can view this QR code"
        )

    # QR is available only after NGO acceptance
    if d.status != "accepted":
        raise HTTPException(
            status_code=409,
            detail="QR available only for accepted donations"
        )

    # Generate the unique pickup QR code
    img = qrcode.make(d.qr_token)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"}
    )


@app.post('/api/donations/{donation_id}/pickup')
def pickup(donation_id:int,body:ScanIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    d=db.get(Donation,donation_id)
    if not d or d.accepted_ngo_id!=user.id:raise HTTPException(404,'Donation not assigned to this NGO')
    if d.status!='accepted':raise HTTPException(409,'Donation not in accepted state')
    if not secrets.compare_digest(body.token,d.qr_token):raise HTTPException(403,'Invalid QR verification token')
    d.status='picked_up';log(db,d.id,'ngo','picked_up','Verified QR pickup recorded',user.id);db.commit()
    return {'status':'picked_up'}

@app.post('/api/donations/{donation_id}/complete')
def complete(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    d=db.get(Donation,donation_id)
    if not d or d.accepted_ngo_id!=user.id:raise HTTPException(404,'Donation not assigned to this NGO')
    if d.status!='picked_up':raise HTTPException(409,'Pickup must be verified before handover')
    d.status='completed';log(db,d.id,'ngo','completed','NGO confirmed food received',user.id);db.commit()
    return {'status':'completed'}

@app.get('/api/admin/users')
def admin_users(user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin');return [serial_user(u) for u in db.scalars(select(User).order_by(User.id.desc())).all()]

@app.patch('/api/admin/users/{user_id}/verify')
def verify_user(user_id:int,body:VerifyIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin');target=db.get(User,user_id)
    if not target or target.role=='admin':raise HTTPException(404,'Account not found')
    target.verified=body.verified;log(db,None,'admin','account_verified' if body.verified else 'verification_revoked',f'User {user_id}',user.id);db.commit()
    return serial_user(target)

@app.get('/api/reports')
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

@app.get('/api/stats')
def stats(user:User=Depends(current_user),db:Session=Depends(db_session)):
    rows=db.scalars(select(Donation)).all()
    if user.role=='provider':rows=[d for d in rows if d.provider_id==user.id]
    if user.role=='ngo':rows=[d for d in rows if d.accepted_ngo_id==user.id or d.id in set(db.scalars(select(Offer.donation_id).where(Offer.ngo_id==user.id)).all())]
    return {'total':len(rows),'available':sum(d.status=='available' for d in rows),'active':sum(d.status in ('accepted','picked_up') for d in rows),'completed':sum(d.status=='completed' for d in rows),'meals':sum(d.quantity for d in rows if d.status=='completed')}

@app.post('/api/demo/seed')
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
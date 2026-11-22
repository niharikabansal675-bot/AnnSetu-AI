from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

@router.post('/api/auth/register', status_code=201)
def register(body: RegisterIn, db: Session=Depends(db_session)):
    if db.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,'Email already registered')
    user=User(name=body.name,email=body.email.lower(),password_hash=password_hash(body.password),role=body.role,organisation=body.organisation,locality=body.locality,capacity=body.capacity,verified=False)
    db.add(user); db.commit(); db.refresh(user)
    return {'token':token_for(user),'user':serial_user(user)}

@router.post('/api/auth/login')
def login(body: LoginIn,db:Session=Depends(db_session)):
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not check_password(body.password,user.password_hash): raise HTTPException(401,'Invalid email or password')
    return {'token':token_for(user),'user':serial_user(user)}

@router.get('/api/me')
def get_me(user:User=Depends(current_user)): return serial_user(user)

from __future__ import annotations
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .config import JWT_SECRET
from .database import db_session
from .models import User

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

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(db_session)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401, 'Please sign in')
    try: user_id = int(jwt.decode(authorization[7:], JWT_SECRET, algorithms=['HS256'])['sub'])
    except Exception: raise HTTPException(401, 'Session expired or invalid')
    user = db.get(User, user_id)
    if not user: raise HTTPException(401, 'Account not found')
    return user

def require_role(user, *roles):
    if user.role not in roles: raise HTTPException(403, 'Not allowed for this account')
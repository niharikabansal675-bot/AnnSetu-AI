"""Create an admin login locally: python create_admin.py"""
import getpass
from sqlalchemy import select
from main import Base, engine, SessionLocal, User, password_hash
Base.metadata.create_all(engine)
email=input('Admin email: ').strip().lower()
name=input('Admin name: ').strip()
pwd=getpass.getpass('Password (8+ characters): ')
if len(pwd)<8: raise SystemExit('Password must be at least 8 characters')
with SessionLocal() as db:
    if db.scalar(select(User).where(User.email==email)): raise SystemExit('Email already exists')
    db.add(User(name=name,email=email,password_hash=password_hash(pwd),role='admin',organisation='Food Rescue',locality='Ghaziabad',verified=True))
    db.commit()
print('Admin account created.')

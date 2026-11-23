import unittest
from datetime import timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base
from app.models import User, Donation, Offer, Audit
from app.schemas import OfferAction
from app.security import utcnow
from app.routers.offers import respond


class OfferResponseTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite+pysqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db=Session(self.engine, expire_on_commit=False)
        self.provider=User(name='Example Provider',email='provider@example.invalid',password_hash='x',role='provider',organisation='Provider',locality='Indirapuram',verified=True,is_demo=True)
        self.ngo=User(name='Example NGO',email='ngo@example.invalid',password_hash='x',role='ngo',organisation='NGO',capacity=100,locality='Indirapuram',verified=True,is_demo=True)
        self.db.add_all([self.provider,self.ngo]);self.db.flush()
        now=utcnow()
        self.donation=Donation(provider_id=self.provider.id,title='Demo meals',food_type='Vegetarian',quantity=25,locality='Indirapuram',address='Synthetic address',prepared_at=now,storage='Covered',deadline=now+timedelta(hours=3),status='available',is_demo=True)
        self.db.add(self.donation);self.db.flush()
        self.offer=Offer(donation_id=self.donation.id,ngo_id=self.ngo.id,status='pending',expires_at=now+timedelta(minutes=15))
        self.db.add(self.offer);self.db.commit()

    def tearDown(self):
        self.db.close();Base.metadata.drop_all(self.engine);self.engine.dispose()

    def test_accept_updates_donation_and_offer(self):
        result=respond(self.offer.id,OfferAction(decision='accept'),self.ngo,self.db)
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(self.donation.status,'accepted')
        self.assertEqual(self.donation.accepted_ngo_id,self.ngo.id)
        self.assertEqual(self.db.scalar(select(Audit.action).where(Audit.donation_id==self.donation.id)),'offer_accepted')

    def test_decline_keeps_donation_available(self):
        result=respond(self.offer.id,OfferAction(decision='decline'),self.ngo,self.db)
        self.assertEqual(result['status'],'declined')
        self.assertEqual(self.donation.status,'available')

    def test_repeated_response_rejected(self):
        respond(self.offer.id,OfferAction(decision='decline'),self.ngo,self.db)
        with self.assertRaises(HTTPException) as cm:
            respond(self.offer.id,OfferAction(decision='accept'),self.ngo,self.db)
        self.assertEqual(cm.exception.status_code,409)

    def test_demo_ngo_cannot_accept_real_donation(self):
        self.donation.is_demo=False;self.db.commit()
        with self.assertRaises(HTTPException) as cm:
            respond(self.offer.id,OfferAction(decision='accept'),self.ngo,self.db)
        self.assertEqual(cm.exception.status_code,403)
        self.assertEqual(self.offer.status,'pending')

    def test_real_ngo_cannot_accept_demo_donation(self):
        self.ngo.is_demo=False;self.db.commit()
        with self.assertRaises(HTTPException) as cm:
            respond(self.offer.id,OfferAction(decision='accept'),self.ngo,self.db)
        self.assertEqual(cm.exception.status_code,403)

    def test_expired_offer_rejected(self):
        self.offer.expires_at=utcnow()-timedelta(seconds=1);self.db.commit()
        with self.assertRaises(HTTPException) as cm:
            respond(self.offer.id,OfferAction(decision='accept'),self.ngo,self.db)
        self.assertEqual(cm.exception.status_code,409)

    def test_unverified_ngo_cannot_accept(self):
        self.ngo.verified=False;self.db.commit()
        with self.assertRaises(HTTPException) as cm:
            respond(self.offer.id,OfferAction(decision='accept'),self.ngo,self.db)
        self.assertEqual(cm.exception.status_code,403)

    def test_already_assigned_donation_rejected(self):
        self.donation.status='accepted';self.db.commit()
        with self.assertRaises(HTTPException) as cm:
            respond(self.offer.id,OfferAction(decision='accept'),self.ngo,self.db)
        self.assertEqual(cm.exception.status_code,409)

if __name__=='__main__': unittest.main()

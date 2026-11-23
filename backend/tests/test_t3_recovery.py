import unittest
from datetime import timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Audit, Donation, Offer, User
from app.security import utcnow
from app.agents.T3.recovery import reconcile_demo_offers
from app.agents.T3.tools import inspect_donation
from app.agents.T3.planner import plan_next_action
from app.agents.T3.state import Candidate


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite+pysqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        provider = User(name='Demo Provider', email='provider@example.invalid', password_hash='x', role='provider',
                        organisation='Provider', locality='Indirapuram', verified=True, is_demo=True)
        ngo1 = User(name='NGO 1', email='ngo1@example.invalid', password_hash='x', role='ngo',
                    organisation='NGO 1', locality='Indirapuram', capacity=50, verified=True, is_demo=True)
        ngo2 = User(name='NGO 2', email='ngo2@example.invalid', password_hash='x', role='ngo',
                    organisation='NGO 2', locality='Vaishali', capacity=50, verified=True, is_demo=True)
        self.db.add_all([provider, ngo1, ngo2]); self.db.flush()
        self.ngo1, self.ngo2 = ngo1, ngo2
        now = utcnow()
        self.donation = Donation(provider_id=provider.id, title='Synthetic food', food_type='Vegetarian', quantity=10,
                                 locality='Indirapuram', address='Synthetic only', prepared_at=now,
                                 storage='Covered', deadline=now+timedelta(hours=3), status='available', is_demo=True)
        self.db.add(self.donation); self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def offer(self, ngo, status='pending', minutes=15):
        o = Offer(donation_id=self.donation.id, ngo_id=ngo.id, status=status,
                  expires_at=utcnow()+timedelta(minutes=minutes))
        self.db.add(o); self.db.commit()
        return o

    def test_no_offers_is_ready(self):
        result = reconcile_demo_offers(self.db, self.donation.id)
        self.assertEqual(result.status, 'ready')
        self.assertEqual(result.timed_out_offer_ids, ())

    def test_active_pending_offer_waits(self):
        self.offer(self.ngo1)
        result = reconcile_demo_offers(self.db, self.donation.id)
        self.assertEqual(result.status, 'waiting')
        self.assertEqual(self.db.scalar(select(Offer.status)), 'pending')

    def test_expired_pending_marked_timed_out_and_audited(self):
        offer = self.offer(self.ngo1, minutes=-1)
        result = reconcile_demo_offers(self.db, self.donation.id)
        self.assertEqual(result.status, 'ready')
        self.assertEqual(result.timed_out_offer_ids, (offer.id,))
        self.assertEqual(self.db.get(Offer, offer.id).status, 'timed_out')
        self.assertEqual(self.db.scalar(select(Audit.action)), 't3_offer_timed_out')

    def test_reconciliation_is_idempotent(self):
        self.offer(self.ngo1, minutes=-1)
        reconcile_demo_offers(self.db, self.donation.id)
        reconcile_demo_offers(self.db, self.donation.id)
        self.assertEqual(len(self.db.scalars(select(Audit)).all()), 1)

    def test_declined_ngo_excluded_by_next_plan(self):
        self.offer(self.ngo1, status='declined')
        state = inspect_donation(self.db, self.donation.id)
        self.assertIn(self.ngo1.id, state.previous_ngo_ids)
        state.phase='evaluated'
        state.candidates=[Candidate(ngo_id=self.ngo1.id,capacity=50,straight_line_km=1,method='test'),
                          Candidate(ngo_id=self.ngo2.id,capacity=50,straight_line_km=2,method='test')]
        result = plan_next_action(state)
        self.assertEqual(result.proposed_action, 'offer')
        self.assertEqual(result.proposed_ngo_id, self.ngo2.id)

    def test_timed_out_ngo_excluded_by_next_plan(self):
        self.offer(self.ngo1, minutes=-1)
        reconcile_demo_offers(self.db, self.donation.id)
        state = inspect_donation(self.db, self.donation.id)
        self.assertIn(self.ngo1.id, state.previous_ngo_ids)
        state.phase='evaluated'
        state.candidates=[Candidate(ngo_id=self.ngo1.id,capacity=50,straight_line_km=1,method='test'),
                          Candidate(ngo_id=self.ngo2.id,capacity=50,straight_line_km=2,method='test')]
        result = plan_next_action(state)
        self.assertEqual(result.proposed_ngo_id, self.ngo2.id)

    def test_real_donation_never_modified(self):
        offer = self.offer(self.ngo1, minutes=-1)
        self.donation.is_demo=False; self.db.commit()
        result = reconcile_demo_offers(self.db, self.donation.id)
        self.assertEqual(result.status, 'forbidden')
        self.assertEqual(self.db.get(Offer,offer.id).status,'pending')

    def test_completed_donation_stops(self):
        offer = self.offer(self.ngo1, minutes=-1)
        self.donation.status='completed'; self.db.commit()
        result = reconcile_demo_offers(self.db, self.donation.id)
        self.assertEqual(result.status, 'stopped')
        self.assertEqual(self.db.get(Offer,offer.id).status,'pending')

    def test_expired_donation_stops(self):
        self.donation.deadline=utcnow()-timedelta(hours=1); self.db.commit()
        self.assertEqual(reconcile_demo_offers(self.db,self.donation.id).status,'stopped')

    def test_missing_donation_not_found(self):
        self.assertEqual(reconcile_demo_offers(self.db,99999).status,'not_found')

    def test_multiple_expired_and_active_waits(self):
        first=self.offer(self.ngo1,minutes=-1)
        second=self.offer(self.ngo2,minutes=10)
        result=reconcile_demo_offers(self.db,self.donation.id)
        self.assertEqual(result.status,'waiting')
        self.assertEqual(result.timed_out_offer_ids,(first.id,))
        self.assertEqual(self.db.get(Offer,second.id).status,'pending')


if __name__=='__main__':
    unittest.main()

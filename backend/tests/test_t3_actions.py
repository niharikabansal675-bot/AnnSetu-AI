import unittest
from datetime import timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import User, Donation, Offer, Audit
from app.security import utcnow
from app.agents.T3.state import AgentState, Candidate
from app.agents.T3.graph import GraphResult
from app.agents.T3.actions import execute_planned_offer


class TestActions(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.provider = User(name='Demo P',email='p@test.invalid',password_hash='x',role='provider',organisation='Test',locality='Indirapuram',capacity=0,verified=True,is_demo=True)
        self.ngo = User(name='Demo N',email='n@test.invalid',password_hash='x',role='ngo',organisation='Test NGO',locality='Indirapuram',capacity=80,verified=True,is_demo=True)
        self.db.add_all([self.provider, self.ngo]);self.db.flush()
        self.donation = Donation(provider_id=self.provider.id, title='Test dinner',food_type='Vegetarian',quantity=50,
            locality='Indirapuram',address='Synthetic test location',prepared_at=utcnow()-timedelta(minutes=10),
            storage='Covered containers',deadline=utcnow()+timedelta(hours=2),status='available',is_demo=True)
        self.db.add(self.donation);self.db.commit()

    def tearDown(self):
        self.db.close();self.engine.dispose()

    def proposal(self, ngo_id=None):
        id = self.ngo.id if ngo_id is None else ngo_id
        state = AgentState(donation_id=self.donation.id,phase='verified',donation_status='available', quantity=50,
            deadline=self.donation.deadline.isoformat(),candidates=[Candidate(id,80,1.5,'SIMULATION locality approximation')],
            proposed_action='offer',proposed_ngo_id=id)
        return GraphResult(state=state,nodes_visited=('observe','evaluate','plan','verify'))

    def count(self):
        return len(self.db.scalars(select(Offer)).all())

    def test_default_is_read_only(self):
        self.assertEqual(execute_planned_offer(self.db, self.proposal()).status,'disabled')
        self.assertEqual(self.count(),0)

    def test_eligible_demo_creates_one_audited_offer(self):
        r=execute_planned_offer(self.db,self.proposal(),enable_writes=True)
        self.assertEqual(r.status,'created');self.assertIsNotNone(r.offer_id)
        self.assertEqual(self.count(),1)
        self.assertEqual(self.db.get(Offer,r.offer_id).status,'pending')
        self.assertEqual(self.db.scalar(select(Audit.action)),'t3_offer_created')

    def test_second_attempt_is_blocked(self):
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'created')
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'skipped')
        self.assertEqual(self.count(),1)

    def test_unverified_ngo_is_blocked(self):
        self.ngo.verified=False;self.db.commit()
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'skipped')
        self.assertEqual(self.count(),0)

    def test_reduced_capacity_is_blocked(self):
        self.ngo.capacity=20;self.db.commit()
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'skipped')

    def test_deadline_close_is_blocked(self):
        self.donation.deadline=utcnow()+timedelta(minutes=15);self.db.commit()
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'skipped')

    def test_status_changed_is_blocked(self):
        self.donation.status='accepted';self.db.commit()
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'skipped')

    def test_nonverified_graph_is_blocked(self):
        p=self.proposal();p.state.phase='planned'
        self.assertEqual(execute_planned_offer(self.db,p,enable_writes=True).status,'skipped')

    def test_real_donation_has_no_sqlite_geographic_fallback(self):
        self.donation.is_demo=False;self.ngo.is_demo=False;self.db.commit()
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'skipped')

    def test_other_active_offer_blocks_creation(self):
        other = User(name='Other NGO',email='other@test.invalid',password_hash='x',role='ngo',organisation='Other',locality='Indirapuram',capacity=80,verified=True,is_demo=True)
        self.db.add(other);self.db.flush()
        self.db.add(Offer(donation_id=self.donation.id,ngo_id=other.id,status='pending',expires_at=utcnow()+timedelta(minutes=10)))
        self.db.commit()
        self.assertEqual(execute_planned_offer(self.db,self.proposal(),enable_writes=True).status,'skipped')


if __name__ == '__main__': unittest.main()

import os
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Donation, User, Offer
from app.security import utcnow
from app.agents.T3.scheduler import cycle_demo_donations
from app.routers.coordinator import run_coordinator


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite+pysqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        provider = User(name='Demo', email='d@test.invalid', password_hash='x', role='provider',
                        organisation='Test', is_demo=True, verified=True)
        real_provider = User(name='Real', email='r@test.invalid', password_hash='x', role='provider',
                             organisation='Test', is_demo=False, verified=True)
        self.db.add_all([provider, real_provider]); self.db.flush()
        now = utcnow()
        self.demo = Donation(provider_id=provider.id, title='Demo food', food_type='Veg', quantity=10,
                             locality='Indirapuram', address='test', prepared_at=now, storage='covered',
                             deadline=now + timedelta(hours=3), status='available', is_demo=True)
        self.real = Donation(provider_id=real_provider.id, title='Real food', food_type='Veg', quantity=10,
                             locality='Indirapuram', address='test', prepared_at=now, storage='covered',
                             deadline=now + timedelta(hours=3), status='available', is_demo=False)
        self.db.add_all([self.demo, self.real]); self.db.commit()

    def tearDown(self):
        self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose()

    @patch('app.agents.T3.scheduler.evaluate_donation')
    def test_preview_only_evaluates_demo(self, evaluate):
        evaluate.return_value = SimpleNamespace(state=SimpleNamespace(proposed_action='offer'))
        output = cycle_demo_donations(self.db, write=False)
        self.assertEqual(output['processed'], 1)
        self.assertEqual(output['offers_created'], [])
        evaluate.assert_called_once()
        self.assertEqual(evaluate.call_args.args[1], self.demo.id)
        self.assertEqual(self.db.scalars(select(Offer)).all(), [])

    def test_sqlite_cannot_write(self):
        with self.assertRaises(RuntimeError):
            cycle_demo_donations(self.db, write=True)

    def test_limit_bound(self):
        with self.assertRaises(ValueError):
            cycle_demo_donations(self.db, limit=0)
        with self.assertRaises(ValueError):
            cycle_demo_donations(self.db, limit=101)

    @patch('app.agents.T3.scheduler.evaluate_donation', side_effect=RuntimeError('test failure'))
    def test_per_donation_error_is_bounded(self, _):
        output = cycle_demo_donations(self.db)
        self.assertEqual(len(output['errors']), 1)
        self.assertEqual(output['errors'][0]['error_type'], 'RuntimeError')
        self.assertEqual(self.db.scalars(select(Offer)).all(), [])

    @patch.dict(os.environ, {'T3_COORDINATOR_MODE': 'preview'})
    def test_legacy_manual_endpoint_paused_in_preview(self):
        with self.assertRaises(HTTPException) as ctx:
            run_coordinator(user=SimpleNamespace(role='admin'), db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)

    @patch.dict(os.environ, {'T3_COORDINATOR_MODE': 'demo'})
    def test_legacy_manual_endpoint_paused_in_demo(self):
        with self.assertRaises(HTTPException) as ctx:
            run_coordinator(user=SimpleNamespace(role='admin'), db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException

from app.routers.t3_execute import t3_execute
from app.agents.T3.actions import execute_planned_offer
from app.agents.T3.graph import GraphResult
from app.agents.T3.state import AgentState


class ControlledExecutionTests(unittest.TestCase):
    def setUp(self):
        self.admin = SimpleNamespace(role='admin')
        self.provider = SimpleNamespace(role='provider')
        self.db = MagicMock()
        self.db.bind.dialect.name = 'postgresql'
        self.db.get.return_value = SimpleNamespace(id=9, is_demo=True)

    @patch.dict('os.environ', {'T3_DEMO_EXECUTION_ENABLED': 'false'})
    def test_default_disabled(self):
        with self.assertRaises(HTTPException) as exc:
            t3_execute(9, False, self.admin, self.db)
        self.assertEqual(exc.exception.status_code, 403)
        self.db.get.assert_not_called()

    @patch.dict('os.environ', {'T3_DEMO_EXECUTION_ENABLED': 'true'})
    def test_admin_only(self):
        with self.assertRaises(HTTPException) as exc:
            t3_execute(9, False, self.provider, self.db)
        self.assertEqual(exc.exception.status_code, 403)

    @patch.dict('os.environ', {'T3_DEMO_EXECUTION_ENABLED': 'true'})
    def test_postgres_required(self):
        self.db.bind.dialect.name = 'sqlite'
        with self.assertRaises(HTTPException) as exc:
            t3_execute(9, False, self.admin, self.db)
        self.assertEqual(exc.exception.status_code, 503)

    @patch.dict('os.environ', {'T3_DEMO_EXECUTION_ENABLED': 'true'})
    def test_real_donation_rejected(self):
        self.db.get.return_value = SimpleNamespace(id=9, is_demo=False)
        with self.assertRaises(HTTPException) as exc:
            t3_execute(9, False, self.admin, self.db)
        self.assertEqual(exc.exception.status_code, 403)

    @patch.dict('os.environ', {'T3_DEMO_EXECUTION_ENABLED': 'true'})
    @patch('app.routers.t3_execute.execute_planned_offer')
    @patch('app.routers.t3_execute.evaluate_donation')
    def test_non_offer_never_writes(self, evaluate, executor):
        s = AgentState(donation_id=9, proposed_action='wait')
        evaluate.return_value = GraphResult(s, ('observe', 'plan', 'verify'))
        result = t3_execute(9, False, self.admin, self.db)
        self.assertEqual(result['write_status'], 'skipped')
        executor.assert_not_called()

    def test_action_defaults_to_no_writes(self):
        state = AgentState(donation_id=9, proposed_action='offer', proposed_ngo_id=8)
        outcome = execute_planned_offer(self.db, GraphResult(state, ('observe','evaluate','plan','verify')))
        self.assertEqual(outcome.status, 'disabled')
        self.db.scalar.assert_not_called()

    @patch.dict('os.environ', {'T3_DEMO_EXECUTION_ENABLED': 'true'})
    @patch('app.routers.t3_execute.execute_planned_offer')
    @patch('app.routers.t3_execute.evaluate_donation')
    def test_valid_proposal_delegates_to_executor(self, evaluate, executor):
        s = AgentState(donation_id=9, proposed_action='offer', proposed_ngo_id=8)
        evaluate.return_value = GraphResult(s, ('observe','evaluate','plan','verify'))
        executor.return_value = SimpleNamespace(status='created', reason='OK', donation_id=9, offer_id=2, ngo_id=8)
        result = t3_execute(9, False, self.admin, self.db)
        self.assertTrue(result['offer_created'])
        executor.assert_called_once()
        self.assertTrue(executor.call_args.kwargs['enable_writes'])

    @patch.dict('os.environ', {'T3_DEMO_EXECUTION_ENABLED': 'true'})
    @patch('app.routers.t3_execute.evaluate_donation', side_effect=RuntimeError('sensitive DB error'))
    def test_failure_rolls_back_and_hides_error(self, _):
        with self.assertRaises(HTTPException) as exc:
            t3_execute(9, False, self.admin, self.db)
        self.assertEqual(exc.exception.status_code, 503)
        self.assertNotIn('sensitive', exc.exception.detail)
        self.db.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main()

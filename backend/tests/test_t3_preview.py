import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from app.agents.T3.graph import GraphResult
from app.agents.T3.state import AgentState
from app.routers.t3_preview import t3_preview


class PreviewEndpointTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.get.return_value = object()
        self.user = MagicMock(role='admin')

    @patch('app.routers.t3_preview.evaluate_donation')
    def test_dry_run_does_not_execute_actions(self, evaluate):
        evaluate.return_value = GraphResult(
            AgentState(donation_id=9, phase='verified', proposed_action='wait'),
            ('observe', 'plan', 'verify'),
        )
        result = t3_preview(9, False, self.user, self.db)
        self.assertEqual(result['mode'], 'dry_run')
        self.assertFalse(result['writes_enabled'])
        self.assertFalse(result['offer_created'])
        self.assertEqual(result['state']['proposed_action'], 'wait')
        evaluate.assert_called_once_with(self.db, 9, include_road=False)

    @patch('app.routers.t3_preview.evaluate_donation')
    def test_optional_road_evaluation_is_forwarded(self, evaluate):
        evaluate.return_value = GraphResult(AgentState(donation_id=2), ('observe',))
        t3_preview(2, True, self.user, self.db)
        evaluate.assert_called_once_with(self.db, 2, include_road=True)

    @patch('app.routers.t3_preview.evaluate_donation')
    def test_missing_donation_is_404(self, evaluate):
        self.db.get.return_value = None
        with self.assertRaises(HTTPException) as context:
            t3_preview(999, False, self.user, self.db)
        self.assertEqual(context.exception.status_code, 404)
        evaluate.assert_not_called()

    @patch('app.routers.t3_preview.evaluate_donation')
    def test_internal_failure_is_sanitized(self, evaluate):
        evaluate.side_effect = RuntimeError('private connection detail')
        with self.assertRaises(HTTPException) as context:
            t3_preview(1, False, self.user, self.db)
        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('private', context.exception.detail)

    @patch('app.routers.t3_preview.evaluate_donation')
    def test_non_admin_denied(self, evaluate):
        self.user.role='provider'
        with self.assertRaises(HTTPException) as context:
            t3_preview(1, False, self.user, self.db)
        self.assertEqual(context.exception.status_code, 403)
        evaluate.assert_not_called()


if __name__ == '__main__':
    unittest.main()

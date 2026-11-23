
import unittest
from datetime import datetime, timedelta, timezone

from app.agents.T3.graph import evaluate_donation, verify_proposal
from app.agents.T3.state import AgentState, Candidate

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)


def observed(*, status='available', pending=None):
    return AgentState(donation_id=42, donation_status=status, quantity=50,
                      deadline=(NOW + timedelta(hours=2)).isoformat(), pending_offer_id=pending)


def eligible(db, state, include_road=False):
    state.phase = 'evaluated'
    state.candidates = [Candidate(ngo_id=7, capacity=100,
                                  straight_line_km=2.1, method='PostGIS')]
    return state


class TestT3Graph(unittest.TestCase):
    def test_offer_read_only(self):
        result = evaluate_donation(None, 42, now=NOW, inspect_tool=lambda db, id: observed(),
                                   eligibility_tool=eligible)
        self.assertEqual(result.state.proposed_action, 'offer')
        self.assertEqual(result.state.proposed_ngo_id, 7)
        self.assertEqual(result.state.phase, 'verified')
        self.assertFalse(result.safe_to_execute)
        self.assertEqual(result.nodes_visited, ('observe', 'evaluate', 'plan', 'verify'))

    def test_pending_skips_evaluation(self):
        def must_not_run(*args, **kwargs):
            raise AssertionError('evaluation must be skipped')
        result = evaluate_donation(None, 42, now=NOW,
                                   inspect_tool=lambda db, id: observed(pending=4),
                                   eligibility_tool=must_not_run)
        self.assertEqual(result.state.proposed_action, 'wait')
        self.assertNotIn('evaluate', result.nodes_visited)

    def test_completed_skips_evaluation(self):
        result = evaluate_donation(None, 42, now=NOW,
                                   inspect_tool=lambda db, id: observed(status='completed'),
                                   eligibility_tool=lambda *a, **k: self.fail('unexpected evaluation'))
        self.assertEqual(result.state.proposed_action, 'none')
        self.assertEqual(result.state.phase, 'verified')

    def test_no_candidates_escalates(self):
        def empty(db, state, include_road=False):
            state.phase = 'evaluated'
            return state
        result = evaluate_donation(None, 42, now=NOW,
                                   inspect_tool=lambda db, id: observed(), eligibility_tool=empty)
        self.assertEqual(result.state.proposed_action, 'escalate')
        self.assertEqual(result.state.phase, 'escalated')

    def test_tool_failure_escalates_without_details(self):
        def fail(*a, **k):
            raise RuntimeError('private database credentials')
        result = evaluate_donation(None, 42, now=NOW,
                                   inspect_tool=lambda db, id: observed(), eligibility_tool=fail)
        self.assertEqual(result.state.proposed_action, 'escalate')
        self.assertTrue(any('RuntimeError' in err for err in result.state.errors))
        self.assertNotIn('private database credentials', str(result.as_dict()))

    def test_tampered_proposal_rejected(self):
        state = observed()
        state.phase = 'planned'
        state.proposed_action = 'offer'
        state.proposed_ngo_id = 99
        state.candidates = [Candidate(ngo_id=7, capacity=100, straight_line_km=1, method='PostGIS')]
        verify_proposal(state)
        self.assertEqual(state.proposed_action, 'escalate')
        self.assertIsNone(state.proposed_ngo_id)

    def test_wrong_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_donation(None, 42, now=NOW,
                              inspect_tool=lambda db, id: AgentState(donation_id=12))

    def test_invalid_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_donation(None, 0)


if __name__ == '__main__':
    unittest.main()


import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agents.T3.state import AgentState, Candidate
from app.agents.T3.planner import plan_next_action

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def state(**kwargs):
    data = dict(donation_id=8, phase='evaluated', donation_status='available', quantity=50,
                deadline=(NOW + timedelta(hours=2)).isoformat(),
                candidates=[Candidate(ngo_id=7, capacity=100, straight_line_km=1.5, method='PostGIS')])
    data.update(kwargs)
    return AgentState(**data)


class TestPlanner(unittest.TestCase):
    def test_offer(self):
        result = plan_next_action(state(), now=NOW)
        self.assertEqual((result.proposed_action, result.proposed_ngo_id), ('offer', 7))

    def test_wait_for_pending(self):
        result = plan_next_action(state(pending_offer_id=12), now=NOW)
        self.assertEqual((result.proposed_action, result.proposed_ngo_id), ('wait', None))

    def test_declined_ngo_not_reselected(self):
        result = plan_next_action(state(previous_ngo_ids=[7], candidates=[
            Candidate(7, 100, 1.5, 'PostGIS'), Candidate(9, 80, 2.5, 'PostGIS')]), now=NOW)
        self.assertEqual(result.proposed_ngo_id, 9)

    def test_no_eligible_ngos(self):
        self.assertEqual(plan_next_action(state(candidates=[]), now=NOW).proposed_action, 'escalate')

    def test_too_late(self):
        result = plan_next_action(state(deadline=(NOW + timedelta(minutes=20)).isoformat()), now=NOW)
        self.assertEqual(result.proposed_action, 'escalate')

    def test_terminal_state(self):
        self.assertEqual(plan_next_action(state(donation_status='completed'), now=NOW).proposed_action, 'none')

    def test_missing_state(self):
        self.assertEqual(plan_next_action(state(deadline=None), now=NOW).proposed_action, 'escalate')

    def test_road_eta_violation(self):
        result = plan_next_action(state(candidates=[Candidate(7, 100, 1.5, 'PostGIS', 3.5, 120)]), now=NOW)
        self.assertEqual(result.proposed_action, 'escalate')

    def test_prefer_road_estimate(self):
        result = plan_next_action(state(candidates=[Candidate(7, 100, 1, 'PostGIS'), Candidate(9, 90, 2, 'PostGIS', 3, 8)]), now=NOW)
        self.assertEqual(result.proposed_ngo_id, 9)

    def test_not_evaluated(self):
        result = plan_next_action(state(phase='observed'), now=NOW)
        self.assertEqual(result.proposed_action, 'wait')

    def test_error_escalates(self):
        result = plan_next_action(state(errors=['PostGIS unavailable']), now=NOW)
        self.assertEqual(result.proposed_action, 'escalate')

    def test_invalid_candidate(self):
        result = plan_next_action(state(candidates=[Candidate(7, 20, 1.5, 'PostGIS')]), now=NOW)
        self.assertEqual(result.proposed_action, 'escalate')


if __name__ == '__main__':
    unittest.main()

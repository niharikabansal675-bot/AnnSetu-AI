import os
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from app.services.t3_explanations import build_decision_payload, get_explanation


class ExplanationBridgeTests(unittest.TestCase):
    def test_offer_payload(self):
        c = SimpleNamespace(ngo_id=8, capacity=70, straight_line_km=2.0)
        s = SimpleNamespace(donation_id=9, proposed_action='offer',
                            proposed_ngo_id=8, candidates=[c], quantity=50,
                            donation_status='available')
        self.assertEqual(build_decision_payload(s)['selected_ngo'], 'NGO 8')

    def test_wait_payload(self):
        s = SimpleNamespace(donation_id=9, proposed_action='wait', donation_status='available')
        self.assertEqual(build_decision_payload(s)['action'], 'wait')

    def test_missing_candidate_escalates(self):
        s = SimpleNamespace(donation_id=9, proposed_action='offer', proposed_ngo_id=8,
                            candidates=[], donation_status='available')
        self.assertEqual(build_decision_payload(s)['action'], 'escalate')

    @patch.dict(os.environ, {'ANNSETU_EXPLANATIONS_ENABLED': 'false'})
    def test_default_does_not_call_network(self):
        with patch('app.services.t3_explanations.urlopen') as urlopen:
            result = get_explanation({'donation_id': 1, 'action': 'stop',
                                      'selected_ngo': None, 'reason_code': 'expired'})
            urlopen.assert_not_called()
        self.assertEqual(result['source'], 'backend_fallback')

    @patch.dict(os.environ, {'ANNSETU_EXPLANATIONS_ENABLED': 'true',
                             'ANNSETU_ML_SERVICE_URL': 'http://127.0.0.1:8100/v1/explain'})
    def test_service_unreachable_uses_fallback(self):
        with patch('app.services.t3_explanations.urlopen', side_effect=OSError('offline')):
            result = get_explanation({'donation_id': 1, 'action': 'stop',
                                      'selected_ngo': None, 'reason_code': 'expired'})
        self.assertEqual(result['source'], 'backend_fallback')

    @patch.dict(os.environ, {'ANNSETU_EXPLANATIONS_ENABLED': 'true',
                             'ANNSETU_ML_SERVICE_URL': 'http://127.0.0.1:8100/v1/explain'})
    def test_service_cannot_override_decision(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = (b'{"donation_id":1,"action":"propose_offer",'
                                      b'"selected_ngo":"NGO 7","source":"model",'
                                      b'"model_used":true,"explanation":"Incorrect action"}')
        response.__enter__.return_value = response
        with patch('app.services.t3_explanations.urlopen', return_value=response):
            result = get_explanation({'donation_id': 1, 'action': 'stop',
                                      'selected_ngo': None, 'reason_code': 'expired'})
        self.assertEqual(result['action'], 'stop')
        self.assertFalse(result['model_used'])

if __name__ == '__main__':
    unittest.main()

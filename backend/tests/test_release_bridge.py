"""Read-only integration contract tests. No database or network needed."""
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app.services.t3_explanations import get_explanation

PAYLOAD = {'donation_id': 9, 'action': 'stop', 'selected_ngo': None, 'reason_code': 'expired'}
CONFIG = {'ANNSETU_EXPLANATIONS_ENABLED': 'true', 'ANNSETU_ML_SERVICE_URL': 'http://127.0.0.1:8100/v1/explain'}


def response(data):
    r = MagicMock()
    r.status = 200
    r.read.return_value = json.dumps(data).encode()
    r.__enter__.return_value = r
    return r


class ReleaseBridgeTests(unittest.TestCase):
    @patch.dict(os.environ, CONFIG)
    def test_service_online_uses_its_fallback(self):
        data = {**PAYLOAD, 'explanation': 'This donation is expired. No offer will be created.',
                'source': 'fallback', 'model_used': False}
        with patch('app.services.t3_explanations.urlopen', return_value=response(data)):
            out = get_explanation(PAYLOAD)
        self.assertEqual(out['source'], 'fallback')
        self.assertEqual(out['action'], 'stop')

    @patch.dict(os.environ, CONFIG)
    def test_offline_uses_backend_fallback(self):
        with patch('app.services.t3_explanations.urlopen', side_effect=ConnectionRefusedError()):
            out = get_explanation(PAYLOAD)
        self.assertEqual(out['source'], 'backend_fallback')
        self.assertFalse(out['model_used'])

    @patch.dict(os.environ, CONFIG)
    def test_timeout_uses_backend_fallback(self):
        with patch('app.services.t3_explanations.urlopen', side_effect=TimeoutError()):
            out = get_explanation(PAYLOAD)
        self.assertEqual(out['source'], 'backend_fallback')

    @patch.dict(os.environ, CONFIG)
    def test_wrong_decision_cannot_override_backend(self):
        data = {**PAYLOAD, 'action': 'propose_offer', 'selected_ngo': 'NGO 8',
                'explanation': 'Offer NGO 8 immediately.', 'source': 'model', 'model_used': True}
        with patch('app.services.t3_explanations.urlopen', return_value=response(data)):
            out = get_explanation(PAYLOAD)
        self.assertEqual(out['source'], 'backend_fallback')
        self.assertEqual(out['action'], 'stop')
        self.assertIsNone(out['selected_ngo'])

    @patch.dict(os.environ, CONFIG)
    def test_invalid_json_uses_backend_fallback(self):
        r = response({})
        r.read.return_value = b'<html>bad gateway</html>'
        with patch('app.services.t3_explanations.urlopen', return_value=r):
            out = get_explanation(PAYLOAD)
        self.assertEqual(out['source'], 'backend_fallback')

    @patch.dict(os.environ, {**CONFIG, 'ANNSETU_ML_SERVICE_URL': 'https://example.org/v1/explain'})
    def test_unreviewed_external_url_blocked(self):
        with patch('app.services.t3_explanations.urlopen') as call:
            out = get_explanation(PAYLOAD)
        call.assert_not_called()
        self.assertEqual(out['source'], 'backend_fallback')


if __name__ == '__main__':
    unittest.main()

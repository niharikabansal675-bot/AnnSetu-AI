import os
import unittest
from fastapi.testclient import TestClient
from ml_service.app import app, validate_generated
from ml_service.schemas import VerifiedDecision

client = TestClient(app)

class ExplanationServiceTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("ANNSETU_USE_MODEL", None)
        os.environ.pop("ANNSETU_SERVICE_KEY", None)

    def test_capacity_fallback(self):
        resp = client.post('/v1/explain', json={
            'donation_id': 9, 'action': 'propose_offer',
            'selected_ngo': 'NGO B', 'reason_code': 'capacity'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['source'], 'fallback')
        self.assertEqual(resp.json()['selected_ngo'], 'NGO B')

    def test_stop_rejects_selected_ngo(self):
        resp = client.post('/v1/explain', json={
            'donation_id': 9, 'action': 'stop', 'selected_ngo': 'NGO B', 'reason_code': 'expired'
        })
        self.assertEqual(resp.status_code, 422)

    def test_wrong_selected_ngo_rejected(self):
        facts = VerifiedDecision(donation_id=1, action='propose_offer', selected_ngo='NGO B', reason_code='capacity')
        output = {'action':'propose_offer','selected_ngo':'NGO A','explanation':'NGO A can collect.'}
        self.assertIsNone(validate_generated(facts, output))

    def test_unsupported_offer_claim_rejected(self):
        facts = VerifiedDecision(donation_id=1, action='propose_offer', selected_ngo='NGO B', reason_code='capacity')
        output = {'action':'propose_offer','selected_ngo':'NGO B','explanation':'No offer was rejected. NGO B qualifies.'}
        self.assertIsNone(validate_generated(facts, output))

    def test_key_required_when_configured(self):
        os.environ['ANNSETU_SERVICE_KEY'] = 'test-secret'
        resp = client.post('/v1/explain', json={'donation_id':1,'action':'stop','reason_code':'expired'})
        self.assertEqual(resp.status_code, 401)

if __name__ == '__main__':
    unittest.main()

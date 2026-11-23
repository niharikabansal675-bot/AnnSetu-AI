"""Tests actual ML app API contract with mocked Qwen, and explicit fallback."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from ml_service.app import app

FACTS = {'donation_id': 9, 'action': 'propose_offer', 'selected_ngo': 'NGO 8', 'reason_code': 'capacity', 'quantity': 25, 'selected_capacity': 30}

class ModelContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch.dict(os.environ, {'ANNSETU_USE_MODEL': 'false', 'ANNSETU_SERVICE_KEY': ''})
    def test_local_fallback_works(self):
        out = self.client.post('/v1/explain', json=FACTS)
        self.assertEqual(out.status_code, 200)
        self.assertEqual(out.json()['source'], 'fallback')
        self.assertFalse(out.json()['model_used'])

    @patch.dict(os.environ, {'ANNSETU_USE_MODEL': 'true', 'ANNSETU_SERVICE_KEY': ''})
    @patch('ml_service.model_loader.generate_json', return_value={
        'action': 'propose_offer', 'selected_ngo': 'NGO 8',
        'explanation': 'NGO 8 has sufficient capacity to handle the proposed offer.'})
    def test_model_validated_response(self, generate):
        out = self.client.post('/v1/explain', json=FACTS)
        self.assertEqual(out.json()['source'], 'model')
        self.assertTrue(out.json()['model_used'])

    @patch.dict(os.environ, {'ANNSETU_USE_MODEL': 'true', 'ANNSETU_SERVICE_KEY': ''})
    @patch('ml_service.model_loader.generate_json', side_effect=MemoryError())
    def test_model_out_of_memory_fallback(self, generate):
        out = self.client.post('/v1/explain', json=FACTS)
        self.assertEqual(out.json()['source'], 'fallback')

    @patch.dict(os.environ, {'ANNSETU_USE_MODEL': 'true', 'ANNSETU_SERVICE_KEY': ''})
    @patch('ml_service.model_loader.generate_json', return_value={
        'action': 'propose_offer', 'selected_ngo': 'NGO 8',
        'explanation': 'No offer was rejected. NGO 8 has sufficient capacity.'})
    def test_unfounded_history_rejected(self, generate):
        out = self.client.post('/v1/explain', json=FACTS)
        self.assertEqual(out.json()['source'], 'fallback')

    @patch.dict(os.environ, {'ANNSETU_USE_MODEL': 'false', 'ANNSETU_SERVICE_KEY': 'secret-test'})
    def test_service_key_required(self):
        out = self.client.post('/v1/explain', json=FACTS)
        self.assertEqual(out.status_code, 401)
        out = self.client.post('/v1/explain', json=FACTS, headers={'X-Service-Key': 'secret-test'})
        self.assertEqual(out.status_code, 200)

if __name__ == '__main__':
    unittest.main()

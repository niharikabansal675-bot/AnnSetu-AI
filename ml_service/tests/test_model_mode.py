import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from ml_service.app import app

client = TestClient(app)
FACTS = {"donation_id": 9, "action": "propose_offer", "selected_ngo": "NGO B", "reason_code": "capacity", "quantity": 25, "selected_capacity": 40}

class ModelModeTests(unittest.TestCase):
    def setUp(self):
        self.old_use = os.environ.get("ANNSETU_USE_MODEL")
        self.old_key = os.environ.get("ANNSETU_SERVICE_KEY")
        os.environ["ANNSETU_USE_MODEL"] = "true"
        os.environ.pop("ANNSETU_SERVICE_KEY", None)

    def tearDown(self):
        if self.old_use is None: os.environ.pop("ANNSETU_USE_MODEL", None)
        else: os.environ["ANNSETU_USE_MODEL"] = self.old_use
        if self.old_key is None: os.environ.pop("ANNSETU_SERVICE_KEY", None)
        else: os.environ["ANNSETU_SERVICE_KEY"] = self.old_key

    @patch("ml_service.model_loader.generate_json")
    def test_valid_model_response(self, generate):
        generate.return_value = {"action": "propose_offer", "selected_ngo": "NGO B", "explanation": "NGO B has sufficient capacity."}
        r = client.post("/v1/explain", json=FACTS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["source"], "model")
        self.assertTrue(r.json()["model_used"])

    @patch("ml_service.model_loader.generate_json")
    def test_model_failure_uses_fallback(self, generate):
        generate.side_effect = RuntimeError("CUDA unavailable")
        r = client.post("/v1/explain", json=FACTS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["source"], "fallback")

    @patch("ml_service.model_loader.generate_json")
    def test_hallucinated_offer_history_rejected(self, generate):
        generate.return_value = {"action": "propose_offer", "selected_ngo": "NGO B", "explanation": "No offer was rejected. NGO B has sufficient capacity."}
        r = client.post("/v1/explain", json=FACTS)
        self.assertEqual(r.json()["source"], "fallback")

    @patch("ml_service.model_loader.generate_json")
    def test_wrong_action_rejected(self, generate):
        generate.return_value = {"action": "stop", "selected_ngo": "NGO B", "explanation": "NGO B has capacity."}
        r = client.post("/v1/explain", json=FACTS)
        self.assertEqual(r.json()["source"], "fallback")

if __name__ == "__main__": unittest.main()

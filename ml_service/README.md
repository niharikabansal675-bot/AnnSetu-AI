# AnnSetu-AI Explanation Microservice (Phase 1)

This is a separate, **explanation-only** FastAPI service. It cannot assign donations, send offers, or change PostgreSQL records. The T3 backend remains the source of truth for candidate eligibility and decisions.

## Install and run a safe local smoke test (Windows PowerShell)

Open a terminal at the `food-rescue-platform` root (not inside `backend`). The ZIP contains a `ml_service` folder; extract it beside `backend` and `frontend`.

```powershell
cd ml_service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
python -m uvicorn ml_service.app:app --host 127.0.0.1 --port 8100
```

Visit `http://127.0.0.1:8100/docs` and test `POST /v1/explain` with:

```json
{
  "donation_id": 9,
  "action": "propose_offer",
  "selected_ngo": "NGO B",
  "reason_code": "capacity",
  "quantity": 50,
  "selected_capacity": 70
}
```

Expected: HTTP 200, `source: "fallback"`, `model_used: false`. This tests the API contract **without loading Qwen**.

Run tests from project root after `httpx` is installed (normally transitively via FastAPI TestClient; if missing run `pip install httpx`):

```powershell
python -m unittest discover -s ml_service/tests -p 'test_*.py' -v
```

## GPU inference (later, on a GPU machine)

1. Upload/extract the downloaded `annsetu_qwen_adapter.zip` to a **private GPU environment**, outside the repository.
2. Install compatible GPU PyTorch, Transformers, PEFT, Accelerate, and the packages in `requirements.txt` in that environment.
3. Set `ANNSETU_ADAPTER_PATH` to that extracted directory; set `ANNSETU_USE_MODEL=true`; set a private `ANNSETU_SERVICE_KEY` and restrict network access.
4. Run this FastAPI service on the GPU machine. The model loads **lazily on the first request**, so initial response can be slower. Do not treat a Kaggle notebook as a persistent public API.
5. The backend T3 integration must be separately implemented and tested. Do **not** let a language model choose NGO IDs or create offers.

## Safety and limitations

- Prototype validation of model-generated explanations is **heuristic**, not a guarantee of factual grounding. To guarantee accurate production wording, display the deterministic `fallback` explanation exclusively or constrain generation to validated reason codes.
- This service accepts **only trusted, backend-verified decisions**. It does not itself validate that any NGO is eligible.
- Do not expose this HTTP service publicly without a service key, TLS, and private network / gateway controls.
- Keep `.env`, credentials, adapters, and large model weights out of GitHub.
- `ANNSETU_USE_MODEL` defaults to false. The first phase should pass local fallback tests before attempting GPU inference.

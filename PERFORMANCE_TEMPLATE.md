# Performance & Results — Measurement Template

Run these tests locally, save exact terminal/browser results and state the environment. **No values have been invented.**

| Scenario | Trial 1 (ms) | Trial 2 (ms) | Trial 3 (ms) | Median (ms) | Expected behavior |
|---|---:|---:|---:|---:|---|
| POST /api/auth/login | | | | | JWT generated for valid credentials |
| POST /api/donations | | | | | Data persists in PostgreSQL |
| POST /api/agent/run (3 NGOs) | | | | | One eligible offer, reason logged |
| POST offer accept | | | | | Exactly one NGO accepts |
| POST pickup with correct QR | | | | | Pickup timestamp recorded |
| POST complete | | | | | Receipt timestamp recorded |

**Environment:** Windows version: ___; Python: ___; PostgreSQL: ___; CPU/RAM: ___; frontend browser: ___; date: ___.

**Suggested validation:** take a before/after screenshot of the same record; verify SQL counts; test 3 repeated cases; run `pytest -v`. Capture bad credentials, invalid QR, duplicate acceptance and no suitable NGO as negative tests.

**Interpretation:** describe the difference between transaction correctness, measured speed and broader social impact. Real-world food-waste reduction has not been measured.

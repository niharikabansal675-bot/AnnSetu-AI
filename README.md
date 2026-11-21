# FOOD RESCUE — Ghaziabad | Milestone 2 implementation

Full-stack capstone prototype with **React/Vite**, **FastAPI**, **PostgreSQL**, role-based verification, bounded coordination agent, QR handover, audit logs, and reports. Flat **navy / blue-white / yellow** theme (no gradients).

> **Important:** This is a tested student MVP and must not be used for live food distribution until NGO verification, food-safety procedures, permissions, privacy, deployment hardening, and real-world operational validation are completed. Real NGO details are **not** bundled. All built-in demo organisations are fictional.

## 1. Quick start on Windows — without Docker

You already have PostgreSQL 18 and `Food_rescue_db`. Keep your **existing database and admin account**. No need to drop tables or reinstall PostgreSQL.

1. Unzip into a new folder. Do **not** overwrite your old `backend/.env` or expose it online. Copy your existing `backend/.env` into the extracted `backend/` folder. If starting fresh, copy `.env.example` to `.env` and fill in a valid `DATABASE_URL` and `JWT_SECRET`. In database URLs, encode `@` as `%40` in passwords. Example format only:
   `postgresql+psycopg://postgres:YOUR_URL_ENCODED_PASSWORD@localhost:5432/Food_rescue_db`
2. Ensure `CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`.
3. In a VS Code **backend** PowerShell terminal:

   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   .\.venv\Scripts\python.exe -m pytest tests -v
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload
   ```

   If you have already created `.venv`, skip creating it. If this is a fresh database, stop the server, run `.\.venv\Scripts\python.exe create_admin.py`, then restart.

4. In a **second** terminal:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

5. Open **http://localhost:3000** for the website; **http://127.0.0.1:8000/docs** for API documentation; and **http://127.0.0.1:8000/api/health** to confirm the backend.

6. In a **third** terminal, optional automatic coordination every 30 seconds:

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe agent_worker.py --interval 30
   ```

   You can also run one cycle from the AI Coordinator dashboard. **Do not run multiple worker processes concurrently** in this prototype.

### SQLite test mode

The automated tests set up an isolated in-memory SQLite database. **They do not change your PostgreSQL data.** For a first-run demo without PostgreSQL, `.env.example` defaults to local SQLite (but PostgreSQL is recommended for demo/presentation).

## 2. The eight integrated modules

| Module | Screens / APIs | Status in this ZIP |
|---|---|---|
| 1. Authentication | Register, sign in, password hashing, role permissions | Implemented, backend tested |
| 2. Admin verification | Administrator screens, verify/revoke API | Implemented, backend tested |
| 3. Donation management | New, list, edit, cancel, deadline/storage validation | Implemented, backend tested |
| 4. Matching | Verified NGO, capacity, locality approximation, time constraints | Implemented, backend tested |
| 5. Coordination agent | Observe offers, rank, send, timeout, decline/reassign, audit, escalation | Implemented, backend tested; optional external LLM |
| 6. NGO acceptance | In-app Accept / Decline with no duplicate acceptance | Implemented, backend tested |
| 7. QR tracking | Authenticated QR image, browser scanner where supported, token fallback, handover, timestamp audit | Implemented; backend tested; browser/device validation pending |
| 8. Reports | Admin reports page, JSON export, overview and audit history | Implemented, backend tested |

### AI explanation and actual constraints

The base coordinator is a **bounded autonomous workflow**, not a trained ML model or a generative LLM. It executes the `observe → evaluate → act → verify` loop through permitted database-backed functions. Its eligibility rules **must** pass before any model sees candidate information.

To enable optional **LLM-assisted ranking**, add **only to your private `backend/.env`**:

```env
ENABLE_LLM_RANKING=true
OPENAI_API_KEY=YOUR_PRIVATE_KEY
OPENAI_MODEL=gpt-4.1-mini
```

The backend sends anonymised shortlist IDs, capacity, approximate area distance and quantity to the language model. The model can choose **only** a candidate already verified as eligible. Invalid output, timeout, and unavailable API fall back to deterministic ranking and record the outcome in the audit reason. This integration needs an internet connection, API credits, and local validation; **do not claim it was live-tested unless you test it with your own key**. No key is needed for the built-in agent workflow.

**Operational limits:** Distance uses illustrative Ghaziabad locality centroids, not road-time or a guaranteed pickup ETA. Availability is not dynamically confirmed yet, and the prototype requires admin verification. QR possession does not independently establish food safety or physical location; use a supervised demo. Camera scanning depends on browser support (native `BarcodeDetector`) and camera permissions. A proper production system should separate collector and provider QR permissions, use signed single-use handover challenges, offer stronger identity checks and add explicit consent.

## 3. How to demonstrate in front of the evaluator

1. Admin logs in and verifies a sample provider and a sample NGO. Never approve fictitious accounts as real-world partners.
2. Provider posts a **confirmed** synthetic listing with future deadline and complete food-handling details.
3. Coordinator produces an auditable offer to an eligible verified NGO.
4. NGO logs in, accepts the offer. System prevents double acceptance.
5. Provider opens **Donations → Track** to display a QR. NGO can scan it on a separate device or paste a token decoded using a trusted QR reader. NGO confirms pickup, then handover.
6. Admin opens **Reports & results**, exports JSON, and shows audit history.
7. Repeat with a declined offer and another eligible NGO for reassignment; repeat with too-large quantity for human escalation.

If the database contains no NGO users, you may click **Seed demo data** to generate fictional examples. Those are labelled simulations and do not represent registered organisations or actual food pickups.

## 4. Test evidence

Run `python -m pytest tests -v` from `backend/` with the virtualenv activated. Expected suite: **12 tests** (8 authentication + 4 integrated workflows). Output from the development environment used to package the ZIP: **12 passed**, with two FastAPI `on_event` deprecation warnings. See `MILESTONE2_EVIDENCE.md` for the rubric evidence table and screenshot checklist. The frontend JSX was syntax-parsed with TypeScript (zero parse diagnostics), **but npm dependency installation and a real browser build could not be completed in the packaging environment**. Run `npm install && npm run build` on Windows for final verification, and include the results in your report.

## 5. Useful endpoints

- `/api/auth/register`, `/api/auth/login`, `/api/me`
- `/api/admin/users`, `/api/admin/users/{id}/verify`
- `/api/donations` (GET/POST), `/api/donations/{id}` (PATCH), `/api/donations/{id}/cancel` (POST)
- `/api/agent/run`, `/api/offers`, `/api/offers/{id}/respond`
- `/api/donations/{id}/qr`, `/api/donations/{id}/pickup`, `/api/donations/{id}/complete`, `/api/donations/{id}/tracking`
- `/api/audit`, `/api/stats`, `/api/reports`, `/api/demo/seed`

## 6. Limits before production

This code is a **prototype**. It does **not** implement: externally verified NGO onboarding, real-time route/availability, FSSAI safety certification, automatic email/SMS alerts, robust multi-worker job leasing, database migrations, rate limiting, password resets, hardened session policies, or production-grade QR anti-replay across devices. Synthetic testing ≠ real-world performance or impact. Protect `.env`, configure a strong JWT secret and run behind HTTPS before any public deployment.

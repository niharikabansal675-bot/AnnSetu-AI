# AnnSetu-AI

### An Agentic AI-Powered Food Rescue and Redistribution Platform

**Connecting surplus food with people who need it through intelligent coordination.**

AnnSetu-AI is a full-stack food rescue platform designed to connect restaurants, food providers, and NGOs to support timely redistribution of surplus food. It combines **Agentic AI coordination, geospatial matching, QR-based handover verification, donation tracking, and an experimental fine-tuned language model**.

**Project status:** Functional local academic prototype; not a production-deployed service.

---

## 1. Problem Statement

Restaurants, events, cafeterias, hostels, and other food providers may generate surplus food. Finding a verified NGO that can collect that food before the pickup deadline can be difficult, especially without coordinated location, capacity, and handover information.

AnnSetu-AI explores how a unified digital platform can improve this coordination process and make donation activity more traceable.

## 2. Project Objectives

- Support organised redistribution of surplus food.
- Connect providers with verified NGOs.
- Coordinate donations using a rule-governed Agentic AI workflow.
- Assess NGO capacity, geographic proximity, and pickup deadlines.
- Allow NGOs to accept or decline offers.
- Support QR-based pickup verification and delivery tracking.
- Maintain activity and audit records.
- Explain backend-verified decisions using an optional fine-tuned Qwen model with a safe fallback.

## 3. Core Features

### Provider Dashboard

Providers can register, log in, list available food, set quantities and pickup deadlines, save pickup locations, view matching progress, and track donation status.

### NGO Dashboard

NGOs can register, maintain their locations and capacities, receive offers, accept or decline requests, and participate in pickup and delivery workflows. Admin verification is required for matching eligibility.

### Admin Dashboard

Administrators can monitor coordination activity, manage verification, review donation information, inspect audit events, and access reporting features.

### NGO Matching

The coordinator checks verified status, available capacity, location, pickup deadline, and previous offers. PostgreSQL/PostGIS provides geographic eligibility checks; OSRM may provide road-network estimates. The selected NGO receives a **pending offer** and retains the choice to accept or decline.

### Pickup, Delivery, and Audit History

The application supports QR-based pickup verification, delivery progress, route visualization when location information is available, and timestamped activity records.

**Donation stages:** `Listed → Accepted → Picked Up → Completed`

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, JavaScript, Vite |
| Backend | Python, FastAPI |
| Database | PostgreSQL 18, PostGIS |
| ORM | SQLAlchemy |
| Routing | OSRM road-network estimates |
| Authentication | JWT |
| Agent orchestration | Python-based T3 workflow |
| Language model | Qwen3-0.6B |
| Fine-tuning | LoRA, Hugging Face Transformers, PEFT |
| GPU development | Kaggle Tesla T4 |
| Version control | Git, GitHub |

## 5. System Architecture

```text
Providers / NGOs / Administrators
               |
        React + Vite UI
               |
         FastAPI Backend
               |
       Auth / Donation APIs
               |
      T3 Agentic AI Workflow
     Observe → Evaluate → Plan → Verify
               |
    Rule-Governed Coordination
               |
      PostgreSQL + PostGIS
               |
       Users / Donations /
       Offers / Audit Events

Optional integrations:
- OSRM for road-network estimates
- Separate ML FastAPI explanation service
  → Fine-tuned Qwen (when GPU is available)
  → Strict validation or deterministic fallback
```

The **backend is the source of truth** for eligibility, actions, and database changes. The language model cannot independently assign an NGO or create an offer.

## 6. T3 Agentic AI

The agent's read-only planning pipeline follows four stages:

1. **Observe:** Read donation status, deadline, quantity, prior offers, and current state.
2. **Evaluate:** Find eligible NGOs based on verification, capacity, location, and other constraints.
3. **Plan:** Propose offering to an NGO, waiting, stopping, or escalating.
4. **Verify:** Check the proposal's consistency and safety conditions.

A separate, controlled execution layer can revalidate database state before writing. **T3 execution is limited to explicitly enabled synthetic demo records**. Normal donation matching currently uses the deterministic legacy coordinator.

Recovery and scheduling modules handle cases such as pending offers, timeouts, and reassignment.

## 7. Fine-Tuned Qwen Explanation Microservice

An independent FastAPI microservice provides explanations of **backend-verified** decisions. It does not create offers, change donation status, or write to PostgreSQL.

### Model training and evaluation

- Base model: **Qwen3-0.6B**.
- Fine-tuning: **LoRA** on **302 synthetic AnnSetu-specific examples**.
- Training environment: **Kaggle Tesla T4 GPU**.
- Scenarios included expiry, pending offers, capacity, verification, pickup deadlines, missing information, and reassignment.
- The adapter was saved and successfully reloaded for separate inference.
- On a 12-case held-out manual evaluation, the fine-tuned model scored **6/12**, the same strict score as the baseline. It is **not sufficiently validated to make autonomous matching decisions**.
- Three targeted GPU integration examples produced accepted model responses after prompt adjustments. This is a limited functionality check, **not proof of factual reliability**.

The service uses a restrictive explanation validator and deterministic fallback if the model is unavailable or its response is not approved. **GPU-backed model inference is not permanently hosted.**

## 8. Geographic Matching and Fairness

For real donations, geographic eligibility uses saved PostGIS coordinates rather than inferred locality names. The local prototype has been tested with a **20 km configured radius**. OSRM estimates road travel time when available; these estimates do **not** include live traffic.

An **experimental workload-aware fair-matching policy** was implemented to compare similarly situated NGOs using historical offer counts. It remains **disabled pending full isolated integration validation**. The current verified policy prioritizes eligible candidates using road estimates and proximity.

## 9. Donation Workflow

```text
Provider creates donation
          |
Pickup location and deadline saved
          |
Coordinator evaluates eligible NGOs
          |
Pending NGO offer created
          |
NGO accepts or declines
          |
QR-based pickup verification
          |
Delivery confirmation
          |
Activity and audit history
```

## 10. Project Structure

```text
food-rescue-platform/
├── frontend/                 # React application
├── backend/
│   ├── app/
│   │   ├── agents/T3/        # State, tools, planning, verification,
│   │   │                     # execution, recovery, scheduling
│   │   ├── routers/          # Auth, donations, offers, admin, T3 routes
│   │   ├── services/         # GIS, routing, explanation bridge
│   │   ├── models.py
│   │   ├── database.py
│   │   └── security.py
│   ├── tests/
│   ├── agent_worker.py
│   └── main.py
├── ml_service/               # Explanation-only FastAPI service
│   ├── app.py
│   ├── model_loader.py
│   ├── schemas.py
│   └── tests/
├── scripts/
├── deploy/
└── README.md
```

## 11. Run Locally (Windows PowerShell)

### Prerequisites

- Python and Node.js/npm
- PostgreSQL with PostGIS enabled
- A local database and backend environment configuration

### Backend

From the repository root:

```powershell
cd backend
# Install dependencies using the backend's maintained dependency file.
# Configure backend/.env locally (never commit it).
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API documentation: `http://127.0.0.1:8000/docs`

### Frontend

In another terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Local frontend: `http://localhost:3000`

### Coordinator worker

From `backend/`, in **one terminal only**:

```powershell
.\.venv\Scripts\python.exe agent_worker.py
```

### ML explanation microservice

From the **repository root**:

```powershell
.\ml_service\.venv\Scripts\python.exe -m uvicorn ml_service.app:app --host 127.0.0.1 --port 8100
```

Service documentation: `http://127.0.0.1:8100/docs`

The default local mode produces deterministic explanations without loading Qwen. GPU inference needs compatible PyTorch/Transformers/PEFT dependencies and the private saved adapter.

### Example non-secret configuration

```dotenv
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
T3_COORDINATOR_MODE=legacy
T3_DEMO_EXECUTION_ENABLED=false
ANNSETU_EXPLANATIONS_ENABLED=true
ANNSETU_ML_SERVICE_URL=http://127.0.0.1:8100/v1/explain
ANNSETU_FAIR_MATCHING=false
```

Also configure a **strong private `JWT_SECRET`** and valid database credentials. Do not commit `.env`, secret keys, backups, or model weights.

## 12. Testing

Local tests and manual verification have covered:

- T3 bridge regression checks (**6 passed**) and ML service contract checks (**5 passed**).
- Read-only health probes for backend (`8000`) and ML service (`8100`).
- Simultaneous acceptance of the same offer and competing offers for one donation (**2 isolated PostgreSQL concurrency cases passed**).
- Simultaneous T3 offer-creation attempts (**1 isolated PostgreSQL race test passed**).
- NGO matching, acceptance, QR pickup, delivery confirmation, and activity history.
- Admin-only endpoint rejection for NGO and provider accounts (**HTTP 403**) and requests without authentication (**HTTP 401**).
- GPU loading of the Qwen base model and LoRA adapter, with restricted response validation.

These checks establish the **tested local prototype behavior**, not comprehensive production readiness.

## 13. Current Limitations

- The application is currently a **local prototype**, not a public production deployment.
- GPU-hosted Qwen inference is not permanently available; deterministic explanations serve as fallback.
- Fair matching remains disabled pending full integration testing.
- OSRM durations are estimates, not live-traffic or guaranteed pickup times.
- Test and simulation data must not be represented as real food deliveries.
- Production security, operational monitoring, scaling, worker uptime, and real-world food safety require further validation.

## 14. Future Work

- Validate and enable workload-aware matching if appropriate.
- Deploy the full stack with secure infrastructure and operational monitoring.
- Expand evaluation of explanation quality and factual grounding.
- Introduce stronger food safety, operational verification, and real-world NGO onboarding.
- Add production-level notifications, monitoring, and recovery procedures.

## 15. Conclusion

AnnSetu-AI demonstrates how Agentic AI, geospatial data, deterministic backend rules, and experimental fine-tuned language-model explanations can support a transparent surplus-food redistribution workflow.

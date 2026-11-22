# AnnSetu-AI | Food Rescue Platform

A full-stack food rescue platform developed as a BCA capstone project, focused on connecting food providers with NGOs in and around Ghaziabad. The aim is to make surplus food donation easier to coordinate and track, from creating a listing to confirming a delivery.

The application has separate workspaces for food providers, NGOs and administrators. It includes location-based NGO matching, an automated coordination workflow, QR-based pickup verification, and optional live location sharing during delivery.

> **Project status:** Working local MVP. The platform has been tested with sample accounts and donations, but it is **not ready for real food distribution**. NGO identity checks, food-safety procedures, privacy and operational safeguards, and production deployment need further work. Demo organisations are fictional.

## Tech stack

| Part | Technology |
| --- | --- |
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL 18 with PostGIS |
| Maps | React Leaflet, OpenStreetMap |
| Location search | Photon-based address autocomplete |
| Road routing | OSRM |
| Authentication | JWT, password hashing, role-based access |
| QR pickup | QR generation and browser-based QR scanning |
| Optional AI integration | OpenAI API for ranking within a pre-approved NGO shortlist |

The interface uses a simple navy, blue, white and yellow theme without gradients.

## Features

### 1. Accounts and verification

Food providers and NGOs can register and sign in. New accounts require administrator approval before participating in live donation workflows. The admin workspace supports account verification and revocation.

### 2. Food donation management

Verified providers can create a donation with the food type, quantity, pickup address, preparation time, storage details and collection deadline. Providers can view their listings, edit eligible listings and cancel donations when allowed by the workflow.

### 3. Location-based NGO matching

PostGIS is used to identify nearby NGOs based on their stored coordinates. The coordinator also checks account verification, capacity, donation type and pickup deadlines before making an offer. For real donations, the system does not guess an NGO's location from a locality name.

### 4. Coordination workflow

The coordinator checks available donations, filters eligible NGOs, ranks suitable candidates and sends offers. NGOs can accept or decline. Expired offers can be marked as timed out, and a later coordinator run can attempt another eligible NGO. Actions are recorded in the activity log.

The main workflow is **rule-based**. It follows an *observe → evaluate → act → verify* structure; it is not a trained machine-learning model. Optional LLM-assisted ranking is available through configuration, but the model cannot bypass the eligibility checks.

### 5. Maps and road routes

Providers and NGOs can set their organisation or pickup location through location search and map controls. The tracking screen displays the pickup point, receiving NGO destination, PostGIS straight-line distance and an OSRM road route when available.

OSRM provides an estimated driving distance and duration. These estimates do **not** include live traffic.

### 6. QR pickup verification

Once an NGO accepts a donation, the provider can display the pickup QR code. The assigned NGO scans the code to confirm collection. The donation then moves from **Accepted** to **Picked Up**.

### 7. Optional collector GPS tracking

After pickup verification, the assigned NGO can allow browser location access and start sharing its current position. The tracking screen shows the reported location, update time and browser-reported accuracy. Sharing can be stopped manually and is cleared when delivery is completed.

Location sharing works while the tracking page is active and the browser continues supplying updates. It is not a background mobile-tracking service. The GPS marker indicates an approximate reported position, not proof of arrival.

### 8. Delivery receipt and audit history

The NGO can record a delivery receipt containing the receiver's name, quantity received, food condition and optional notes. The system logs important events for later review. A receipt currently records the NGO account's declaration; **a separate receiving officer has not independently verified it**.

### 9. Admin reports

The admin workspace provides summaries of donation statuses, offers, coordination activity and completed quantities. These figures represent application records, not independently measured food-distribution outcomes.

## Project structure

```text
food-rescue-platform/
├── backend/
│   ├── main.py
│   ├── agent_worker.py            # optional coordinator worker
│   ├── create_admin.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── tests/
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── components/            # navigation and shared UI
│   │   ├── pages/                 # dashboards and workspaces
│   │   ├── donations/             # donation forms and tracking modal
│   │   ├── maps/                  # map and location search
│   │   ├── tracking/              # QR, GPS and delivery receipt
│   │   ├── services/              # API requests
│   │   ├── utils/                 # shared formatting functions
│   │   └── styles/style.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```

The frontend was divided into smaller React components to make the pages easier to maintain. The backend is still mainly contained in `main.py` and can be modularised later.

## Run locally on Windows

### Requirements

- Python and Node.js/npm
- PostgreSQL with the PostGIS extension enabled in the application database
- A local database and valid database credentials

The project has been developed using a PostgreSQL database named `Food_rescue_db`. If you already have the database, **do not drop or recreate it** just to run the application.

### 1. Backend setup

Open a terminal in the project folder:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Skip the virtual environment creation step if you already have a working one.

Create `backend/.env` using `backend/.env.example` as a reference. Set your PostgreSQL connection string and a strong JWT secret. For example:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_URL_ENCODED_PASSWORD@localhost:5432/Food_rescue_db
JWT_SECRET=REPLACE_WITH_A_LONG_RANDOM_SECRET
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

If your database password contains special URL characters, encode them correctly. Never commit `.env` or API keys to GitHub.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

For a fresh installation, create an admin account using the project's `create_admin.py` script as appropriate. Existing installations should keep their current admin account and database records.

### 2. Frontend setup

Open a second terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

Useful links:

- Frontend: `http://localhost:3000`
- API health: `http://127.0.0.1:8000/api/health`
- FastAPI documentation: `http://127.0.0.1:8000/docs`

Both the frontend and backend servers must be running for login and other API operations to work.

### 3. Optional coordinator worker

The coordinator can be triggered from its dashboard. If using the worker script included with the project, start it in another terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe agent_worker.py --interval 30
```

Do not start multiple copies of the worker in this prototype. The worker is optional for a local demonstration.

## How I test the complete flow

1. Sign in as an administrator and verify a test provider and NGO.
2. Set the relevant locations for the provider pickup and NGO.
3. Create a sample donation with a future pickup deadline.
4. Run the coordinator and check which NGO receives the offer and why.
5. Sign in as the NGO and accept the offer.
6. Open the donation tracking screen to view the pickup point, destination and estimated road route.
7. Display the provider's QR and scan it from the NGO account to record pickup.
8. Enable location sharing, check the collector marker and its update time, then stop sharing.
9. Record the delivery receipt and check that the donation is completed.
10. Review the activity history and admin reports.

For local demonstration, I use synthetic donation records rather than arranging real pickups.

## Tests and checks

The project includes backend tests under `backend/tests`. They can be run from the backend directory with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

The frontend production build can be checked with:

```powershell
cd frontend
npm run build
```

The modular frontend has completed a local Vite build. I have also checked the map and GPS-sharing interface in the browser. Other end-to-end flows should be retested after frontend changes. I am not claiming that the latest codebase has passed every backend test or production-level security test.

## Main API endpoints

| Purpose | Endpoint |
| --- | --- |
| Registration and login | `/api/auth/register`, `/api/auth/login` |
| Account and organisation location | `/api/me`, `/api/me/location` |
| Donations | `/api/donations` |
| Donation location and route | `/api/donations/{id}/geo` |
| Coordinator | `/api/agent/run` |
| NGO offers | `/api/offers`, `/api/offers/{id}/respond` |
| QR pickup verification | `/api/donations/{id}/qr`, `/api/donations/{id}/pickup` |
| Journey and audit details | `/api/donations/{id}/tracking`, `/api/audit` |
| Collector GPS | `/api/donations/{id}/live`, `/live/start`, `/live/update`, `/live/stop` under the same donation path |
| Delivery confirmation | `/api/donations/{id}/delivery-confirm`, `/api/donations/{id}/delivery-receipt` |
| Admin verification | `/api/admin/users`, `/api/admin/users/{id}/verify` |
| Reports and statistics | `/api/reports`, `/api/stats` |

For the full set of available endpoints and request formats, see `/docs` while FastAPI is running.

## Optional LLM-assisted matching

The platform works without an LLM key. If I want to experiment with model-assisted ranking, I can add the following values to my private `backend/.env`:

```env
ENABLE_LLM_RANKING=true
OPENAI_API_KEY=YOUR_PRIVATE_KEY
OPENAI_MODEL=gpt-4.1-mini
```

The model is only allowed to choose from NGOs already approved by the matching rules. The deterministic coordinator remains the fallback if the model is unavailable or returns an invalid choice. This optional integration should be tested separately before reporting it as a demonstrated feature.

## Current limitations

This is still a local MVP. Before anyone uses it for real food distribution, it would need stronger NGO onboarding and identity verification, food-safety review, privacy and consent procedures, HTTPS deployment, database migrations, rate limiting, monitoring, operational support and a more robust background worker.

The road route is an estimate, and browser GPS can become inaccurate or stop updating. A delivery receipt is currently self-attested by the NGO account rather than independently approved by a receiving officer. The system does not establish whether food is safe or whether a donation actually reached its intended beneficiaries.

## Next steps

The immediate focus is on checking the refactored frontend, strengthening automated tests, improving error handling and preparing a reliable deployment. Separate collector and receiving-officer accounts can be considered after the current workflow is stable.
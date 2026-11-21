# Milestone 2 — Rubric evidence packet

**Scope:** Food Rescue, Ghaziabad. Eight modules implemented as a working full-stack MVP, with some production limitations noted below. The claims of automatic tests are confined to the temporary test environment. Do not state that real food has been rescued from synthetic tests.

## 30-mark rubric alignment

| Rubric | Marks | Evidence to attach |
|---|---:|---|
| System / Technical Design | 5 | `ARCHITECTURE.md` diagrams, eight-module breakdown, PostgreSQL schema and access controls |
| MVP implementation | 10 | Admin verification, provider listing, agent offer, NGO acceptance, QR pickup/handover, dashboard screenshots |
| Testing & Validation | 5 | `pytest tests -v` full console, invalid scan/repeated scan/role denial proof, real browser test log |
| Performance & Results | 5 | Repeatable local timings from `PERFORMANCE_TEMPLATE.md`, reports JSON export, documented limits |
| Documentation & Project Management | 5 | This checklist, README and `PROJECT_DIARY.md` with dated entries and responsibilities |

## Verified backend tests (isolated SQLite)

- `test_auth.py`: health, CORS, NGO registration, duplicate email rejection, wrong password, denial of non-admin verification, successful verification, denial of unverified listing.
- `test_workflow.py`: accepted offer → QR pickup → receipt → reports; editing and cancelling; decline and reassignment; no-eligible-NGO escalation.
- **Result when packaged: 12 passed.** Warnings: two FastAPI startup decorator deprecations, not test failures.
- Backend validation does **not** imply PostgreSQL integration, browser camera, deployment or external model verified.

## Screenshots to take using your Windows machine

- [ ] `npm run build` output and website homepage without gradients
- [ ] pgAdmin `Food_rescue_db` tables list; redact personal/secret data
- [ ] NGO registration form and pending verification badge
- [ ] Admin approves test account
- [ ] Provider listing with quantity, preparation, storage and deadline
- [ ] Coordinator recommendation, offer explanation and audit log
- [ ] NGO accepts; second attempt fails / is withdrawn
- [ ] QR presented; authorised pickup; NGO receipt with timestamps
- [ ] Admin report counts and JSON export
- [ ] `pytest -v` successful run and execution duration
- [ ] Negative path: insufficient capacity causes escalation

## Wording to use in Milestone 2 presentation

> We implemented and backend-tested an eight-module Food Rescue MVP covering account control, food listings, NGO matching, a bounded Agentic AI coordination workflow, acceptance, QR tracking and reporting. Twelve automated integration tests passed in an isolated database. Live browser and PostgreSQL validation, external LLM invocation, and real-world NGO/food-safety checks remain separate verification tasks.

Keep quantitative performance claims empty until measured with `PERFORMANCE_TEMPLATE.md`.

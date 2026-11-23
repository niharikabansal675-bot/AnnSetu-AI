"""Independent explanation-only FastAPI service.

T3 must compute all eligibility, decisions and safety checks. This service
must never send offers or mutate donations.
"""
import os
import re
from fastapi import FastAPI, Header, HTTPException
from .schemas import ExplanationResponse, VerifiedDecision

app = FastAPI(title="AnnSetu Explanation Service", version="0.1.0")


def fallback(f: VerifiedDecision) -> str:
    if f.action == "stop":
        return "This donation is no longer eligible for matching. No new NGO offer will be proposed."
    if f.action == "wait":
        return "An NGO offer is pending. Wait for a response or timeout before matching again."
    if f.action == "escalate":
        return "No safe automatic assignment was confirmed. Request human review."
    ngo = f.selected_ngo
    if f.reason_code == "closer_eligible":
        return f"{ngo} is the backend-selected eligible candidate based on proximity. Revalidate before offering."
    if f.reason_code == "capacity":
        return f"{ngo} is the backend-selected candidate with sufficient capacity. Revalidate before offering."
    if f.reason_code == "verification":
        return f"{ngo} is the backend-selected verified candidate. Revalidate before offering."
    if f.reason_code == "declined_reassignment":
        return f"The previous offer was declined. {ngo} is the next proposed candidate, subject to revalidation."
    return f"{ngo} is the backend-selected candidate. Revalidate before creating an offer."



def validate_generated(f: VerifiedDecision, generated: object) -> str | None:
    """Only allow exact, backend-supported explanation statements."""

    if not isinstance(generated, dict):
        return None

    if set(generated) != {"action", "selected_ngo", "explanation"}:
        return None

    if generated["action"] != f.action:
        return None

    if generated["selected_ngo"] != f.selected_ngo:
        return None

    explanation = generated["explanation"]

    if not isinstance(explanation, str):
        return None

    ngo = f.selected_ngo

    # Whitelisted explanations for verified backend decisions.
    approved = {
        ("stop", "expired"): [
            "Donation has expired",
            "This donation has expired",
            "This donation is no longer eligible for matching",
        ],
        ("wait", "pending_offer"): [
            "An NGO offer is pending",
            "An NGO offer is pending. Wait for a response before matching again",
        ],
    }

    if ngo:
        approved[("propose_offer", "capacity")] = [
            f"{ngo} has sufficient capacity to handle the proposed offer",
            f"{ngo} has sufficient capacity and is the proposed candidate",
        ]

    def normalize(value: str) -> str:
        return " ".join(value.casefold().strip().rstrip(".").split())

    allowed = approved.get((f.action, f.reason_code), [])

    if normalize(explanation) not in {
        normalize(item) for item in allowed
    }:
        return None

    return explanation


@app.get("/health")
def health():
    return {"status": "ok", "model_enabled": os.getenv("ANNSETU_USE_MODEL", "false").lower() == "true"}


@app.post("/v1/explain", response_model=ExplanationResponse)
def explain(decision: VerifiedDecision, x_service_key: str | None = Header(default=None)):
    expected_key = os.getenv("ANNSETU_SERVICE_KEY", "")
    if expected_key and x_service_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid service key")
    # No key is permitted ONLY for localhost smoke-testing. Set a service
    # key and private network when deploying; never expose unauthenticated.
    text = fallback(decision)
    source = "fallback"
    if os.getenv("ANNSETU_USE_MODEL", "false").lower() == "true":
        try:
            from .model_loader import generate_json
            candidate = generate_json(decision.model_dump())
            checked = validate_generated(decision, candidate)
            if checked is not None:
                text = checked
                source = "model"
        except Exception:
            # Model unavailable, out of memory, invalid JSON => safe fallback.
            pass
    return ExplanationResponse(
        donation_id=decision.donation_id,
        action=decision.action,
        selected_ngo=decision.selected_ngo,
        explanation=text,
        source=source,
        model_used=(source == "model"),
    )

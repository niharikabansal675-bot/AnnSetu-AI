from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Action = Literal["propose_offer", "wait", "stop", "escalate"]
Reason = Literal[
    "closer_eligible", "capacity", "verification", "expired", "pending_offer",
    "pickup_deadline", "declined_reassignment", "missing_information", "no_eligible_ngo",
]


class VerifiedDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    donation_id: int = Field(ge=1)
    action: Action
    selected_ngo: str | None = Field(default=None, max_length=100)
    reason_code: Reason
    quantity: int | None = Field(default=None, ge=1)
    selected_capacity: int | None = Field(default=None, ge=0)
    selected_distance_km: float | None = Field(default=None, ge=0)
    alternative_ngo: str | None = Field(default=None, max_length=100)
    alternative_capacity: int | None = Field(default=None, ge=0)
    alternative_distance_km: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_decision(self):
        if self.action == "propose_offer" and not self.selected_ngo:
            raise ValueError("propose_offer needs selected_ngo")
        if self.action != "propose_offer" and self.selected_ngo is not None:
            raise ValueError("non-offer actions must not select an NGO")
        if self.reason_code == "expired" and self.action != "stop":
            raise ValueError("expired decisions must stop")
        if self.reason_code == "pending_offer" and self.action != "wait":
            raise ValueError("pending offer decisions must wait")
        return self


class ExplanationResponse(BaseModel):
    donation_id: int
    action: Action
    selected_ngo: str | None
    explanation: str
    source: Literal["model", "fallback"]
    model_used: bool

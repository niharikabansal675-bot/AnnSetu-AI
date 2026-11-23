"""Structured state for a single bounded T3 coordination evaluation.

No credentials, addresses, QR tokens or live GPS positions are stored here.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Phase = Literal['observed', 'evaluated', 'planned', 'acted', 'verified', 'escalated']
Action = Literal['wait', 'offer', 'escalate', 'none']


@dataclass(frozen=True)
class Candidate:
    ngo_id: int
    capacity: int
    straight_line_km: float
    method: str
    road_distance_km: float | None = None
    road_duration_minutes: float | None = None


@dataclass
class AgentState:
    donation_id: int
    phase: Phase = 'observed'
    donation_status: str | None = None
    quantity: int | None = None
    deadline: str | None = None
    candidates: list[Candidate] = field(default_factory=list)
    previous_ngo_ids: list[int] = field(default_factory=list)
    pending_offer_id: int | None = None
    proposed_action: Action = 'none'
    proposed_ngo_id: int | None = None
    reasons: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

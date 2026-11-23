"""T3 coordination dry-run graph: observe -> evaluate -> plan -> verify.

This module deliberately does not create offers, write audit events or update the
DB. The existing coordinator remains the sole live executor until a separately
tested action layer is installed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from .planner import plan_next_action
from .state import AgentState
from .tools import find_eligible_ngos, inspect_donation


@dataclass(frozen=True)
class GraphResult:
    state: AgentState
    nodes_visited: tuple[str, ...]
    safe_to_execute: bool = False  # This dry-run never authorises execution.

    def as_dict(self) -> dict:
        return {
            'state': self.state.as_dict(),
            'nodes_visited': list(self.nodes_visited),
            'safe_to_execute': self.safe_to_execute,
        }


def verify_proposal(state: AgentState) -> AgentState:
    """Check internal consistency of a *proposal*, not a completed delivery.

    Tool functions perform the authoritative database eligibility checks. A
    future executor must revalidate under a transaction before any write.
    """
    if state.proposed_action == 'offer':
        candidate_ids = {candidate.ngo_id for candidate in state.candidates}
        if (state.donation_status != 'available'
                or state.pending_offer_id is not None
                or state.proposed_ngo_id is None
                or state.proposed_ngo_id not in candidate_ids
                or state.proposed_ngo_id in state.previous_ngo_ids):
            state.errors.append('Unsafe offer proposal detected in dry-run verification.')
            state.proposed_action = 'escalate'
            state.proposed_ngo_id = None
            state.phase = 'escalated'
            return state
    else:
        state.proposed_ngo_id = None
    state.phase = 'escalated' if state.proposed_action == 'escalate' else 'verified'
    return state


def evaluate_donation(
    db: Session,
    donation_id: int,
    *,
    include_road: bool = False,
    now: datetime | None = None,
    inspect_tool: Callable[[Session, int], AgentState] = inspect_donation,
    eligibility_tool: Callable[..., AgentState] = find_eligible_ngos,
) -> GraphResult:
    """Run an auditable read-only workflow for one donation.

    `inspect_tool` and `eligibility_tool` are injectable for deterministic unit
    testing. No network or database writes are performed by this orchestration
    layer. The eligibility tool may query PostGIS/OSRM when requested.
    """
    if donation_id <= 0:
        raise ValueError('donation_id must be a positive integer')
    visited = ['observe']
    state = inspect_tool(db, donation_id)
    if state.donation_id != donation_id:
        raise ValueError('Inspector returned an unexpected donation ID')

    # Evaluate only available donations without an outstanding live offer.
    # This also avoids unnecessary OSRM calls for donations already assigned.
    should_evaluate = (
        state.donation_status == 'available'
        and state.pending_offer_id is None
        and state.proposed_action not in ('wait', 'escalate')
        and not state.errors
    )
    if should_evaluate:
        visited.append('evaluate')
        try:
            state = eligibility_tool(db, state, include_road=include_road)
        except Exception as exc:
            # Report error type only: do not leak database/connection details.
            state.errors.append(f'Eligibility tool failed: {type(exc).__name__}')
    visited.append('plan')
    state = plan_next_action(state, now=now)
    visited.append('verify')
    state = verify_proposal(state)
    return GraphResult(state=state, nodes_visited=tuple(visited))
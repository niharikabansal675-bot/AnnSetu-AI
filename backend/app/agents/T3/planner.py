
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .state import AgentState, Candidate

_TERMINAL = {'accepted', 'picked_up', 'completed', 'cancelled', 'expired'}


def _as_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Deadline must include a timezone')
    return parsed.astimezone(timezone.utc)


def plan_next_action(state: AgentState, *, now: datetime | None = None) -> AgentState:
    """Plan offer/wait/escalate/none based solely on an observed, evaluated state.

    Does not mutate external systems, send notifications, or call an LLM.
    The same state may be re-planned; the planner is intentionally idempotent.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    current = current.astimezone(timezone.utc)

    evaluated = state.phase in ('evaluated', 'planned')
    # Reset only the current proposed decision; preserve earlier observations.
    state.proposed_action = 'none'
    state.proposed_ngo_id = None
    state.phase = 'planned'

    if state.errors:
        state.proposed_action = 'escalate'
        state.reasons.append('Agent encountered an error; human review required.')
        return state

    if state.donation_status in _TERMINAL:
        state.reasons.append(f'Donation is {state.donation_status}; matching is not permitted.')
        return state
    if state.donation_status != 'available':
        state.proposed_action = 'escalate'
        state.reasons.append('Donation has an unknown or missing status; human review required.')
        return state

    if state.pending_offer_id is not None:
        state.proposed_action = 'wait'
        state.reasons.append(f'Offer {state.pending_offer_id} is awaiting a response.')
        return state

    if not state.deadline or state.quantity is None or state.quantity <= 0:
        state.proposed_action = 'escalate'
        state.reasons.append('Deadline or quantity information is missing or invalid.')
        return state
    try:
        deadline = _as_utc(state.deadline)
    except (TypeError, ValueError):
        state.proposed_action = 'escalate'
        state.reasons.append('Deadline could not be interpreted safely.')
        return state

    if deadline <= current + timedelta(minutes=30):
        state.proposed_action = 'escalate'
        state.reasons.append('Pickup deadline is within the required 30-minute safety buffer.')
        return state

    if not evaluated:
        # An inspected donation has not necessarily been passed to find_eligible_ngos.
        state.proposed_action = 'wait'
        state.reasons.append('Run NGO eligibility evaluation before selecting a match.')
        return state

    eligible: list[Candidate] = []
    for candidate in state.candidates:
        if (candidate.ngo_id > 0 and candidate.ngo_id not in state.previous_ngo_ids
                and candidate.capacity >= state.quantity
                and candidate.straight_line_km >= 0
                and candidate.road_duration_minutes is not None
                and deadline <= current + timedelta(minutes=max(30, candidate.road_duration_minutes + 15))):
            continue
        if (candidate.ngo_id <= 0 or candidate.ngo_id in state.previous_ngo_ids
                or candidate.capacity < state.quantity or candidate.straight_line_km < 0):
            continue
        eligible.append(candidate)

    if not eligible:
        state.proposed_action = 'escalate'
        state.reasons.append('No eligible, unused NGO remains; administrator review required.')
        return state

    # Follow the current coordinator ranking: prefer verified road estimates,
    # then lower estimated drive time / straight-line distance, then capacity.
    eligible.sort(key=lambda c: (
        c.road_duration_minutes is None,
        c.road_duration_minutes if c.road_duration_minutes is not None else c.straight_line_km,
        c.straight_line_km, -c.capacity, c.ngo_id,
    ))
    selected = eligible[0]
    state.proposed_action = 'offer'
    state.proposed_ngo_id = selected.ngo_id
    if selected.road_duration_minutes is not None:
        explanation = (f'NGO {selected.ngo_id} meets recorded capacity and location checks; '
                       f'estimated drive {selected.road_duration_minutes:.1f} min '
                       '(no live traffic).')
    else:
        explanation = (f'NGO {selected.ngo_id} meets recorded capacity and location checks; '
                       f'distance {selected.straight_line_km:.2f} km; '
                       'road ETA and live availability are unverified.')
    state.reasons.append(explanation + ' Execution must recheck eligibility and donation status.')
    return state

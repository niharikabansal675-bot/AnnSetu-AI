"""Read-only, bounded tools for the proposed T3 Agentic AI workflow.

These functions are for trusted backend code, not public endpoints. They
never bypass matching constraints and never create or modify an offer.
"""
from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...config import GIS_RADIUS_KM
from ...models import Donation, Offer, User
from ...security import aware, utcnow
from ...services.gis import ensure_postgis, point_coordinates
from ...services.routing import driving_route
from .state import AgentState, Candidate


def inspect_donation(db: Session, donation_id: int) -> AgentState:
    """Read donation stage and previous/pending offers without writing."""
    d = db.get(Donation, donation_id)
    if d is None:
        raise ValueError('Donation not found')
    offers = db.scalars(select(Offer).where(Offer.donation_id == donation_id)
                        .order_by(Offer.created_at.desc())).all()
    state = AgentState(
        donation_id=d.id,
        donation_status=d.status,
        quantity=d.quantity,
        deadline=aware(d.deadline).isoformat(),
        previous_ngo_ids=sorted({o.ngo_id for o in offers}),
    )
    active = [o for o in offers if o.status == 'pending' and aware(o.expires_at) > utcnow()]
    if active:
        state.pending_offer_id = active[0].id
        state.proposed_action = 'wait'
        state.reasons.append('An active NGO offer is awaiting response.')
    elif d.status != 'available':
        state.proposed_action = 'none'
        state.reasons.append(f'Donation is {d.status}, not available for matching.')
    elif aware(d.deadline) <= utcnow() + timedelta(minutes=30):
        state.proposed_action = 'escalate'
        state.reasons.append('Less than 30 minutes remain before pickup deadline.')
    return state


def find_eligible_ngos(db: Session, state: AgentState, *, include_road: bool = False,
                       max_road_checks: int = 5) -> AgentState:
    """Find candidates matching current coordinator's fixed safety boundaries.

    Real donations require PostGIS coordinates. Demo donations without a
    pickup coordinate may use the existing simulated locality approximation.
    Dynamic transport availability is NOT supported by the current schema.
    """
    if state.pending_offer_id or state.proposed_action in ('wait', 'escalate'):
        return state
    d = db.get(Donation, state.donation_id)
    if d is None:
        raise ValueError('Donation not found')
    if d.status != 'available':
        state.proposed_action = 'none'
        state.reasons.append('Donation is no longer available.')
        return state
    if aware(d.deadline) <= utcnow() + timedelta(minutes=30):
        state.proposed_action = 'escalate'
        state.reasons.append('Pickup deadline is too close.')
        return state

    ensure_postgis(db)
    has_pickup = bool(db.scalar(text('SELECT pickup_location IS NOT NULL FROM donations WHERE id=:id'),
                                {'id': d.id}))
    distances: dict[int, float] = {}
    if has_pickup:
        rows = db.execute(text('''SELECT u.id AS ngo_id,
            ST_Distance(u.location, d.pickup_location)/1000 AS km
            FROM users u CROSS JOIN donations d
            WHERE d.id=:donation_id AND u.role='ngo' AND u.verified=TRUE
              AND u.capacity>=d.quantity AND u.is_demo=d.is_demo
              AND u.location IS NOT NULL
              AND ST_DWithin(u.location, d.pickup_location, :radius_m)'''),
            {'donation_id': d.id, 'radius_m': GIS_RADIUS_KM * 1000}).mappings().all()
        distances = {int(r['ngo_id']): round(float(r['km']), 2) for r in rows}

    ngos = db.scalars(select(User).where(User.role == 'ngo', User.verified.is_(True),
                                          User.capacity >= d.quantity,
                                          User.is_demo == d.is_demo)).all()
    candidates: list[Candidate] = []
    for ngo in ngos:
        if ngo.id in state.previous_ngo_ids:
            continue
        if has_pickup:
            km = distances.get(ngo.id)
            method = 'PostGIS straight-line'
        elif d.is_demo:
            # Kept deliberately identical to the existing prototype's fallback.
            from ...routers.coordinator import locality_distance
            km = locality_distance(d.locality, ngo.locality)
            method = 'SIMULATION locality approximation'
        else:
            km = None
            method = 'unavailable'
        if km is not None:
            candidates.append(Candidate(ngo_id=ngo.id, capacity=ngo.capacity,
                                        straight_line_km=km, method=method))
    candidates.sort(key=lambda c: (c.straight_line_km, -c.capacity, c.ngo_id))

    if include_road and has_pickup and not d.is_demo:
        pickup = point_coordinates(db, 'donations', 'pickup_location', d.id)
        enriched: list[Candidate] = []
        for index, candidate in enumerate(candidates):
            if index < max(0, min(max_road_checks, 5)) and pickup:
                destination = point_coordinates(db, 'users', 'location', candidate.ngo_id)
                route = driving_route(pickup, destination) if destination else None
                if route:
                    minutes = route['route_duration_minutes']
                    if aware(d.deadline) <= utcnow() + timedelta(minutes=max(30, minutes + 15)):
                        continue
                    candidate = Candidate(ngo_id=candidate.ngo_id, capacity=candidate.capacity,
                                          straight_line_km=candidate.straight_line_km,
                                          method=candidate.method,
                                          road_distance_km=route['route_distance_km'],
                                          road_duration_minutes=minutes)
            enriched.append(candidate)
        candidates = sorted(enriched, key=lambda c: (
            c.road_duration_minutes is None,
            c.road_duration_minutes if c.road_duration_minutes is not None else c.straight_line_km,
            c.straight_line_km, -c.capacity, c.ngo_id))
    state.candidates = candidates
    state.phase = 'evaluated'
    if candidates:
        state.reasons.append(f'{len(candidates)} eligible NGO candidate(s) found; dynamic availability not verified.')
    else:
        state.proposed_action = 'escalate'
        state.reasons.append('No eligible unused NGO candidate found. Human review needed.')
    return state

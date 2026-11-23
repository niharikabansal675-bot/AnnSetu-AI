"""Optional, read-only T3 -> AnnSetu explanation service bridge.

No offer writes, no credentials/addresses/GPS forwarded to the model.
The decision is always computed by T3; service failure returns a local template.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def build_decision_payload(state) -> dict:
    """Translate bounded T3 AgentState into the ML service's validated schema."""
    action = state.proposed_action
    payload = {"donation_id": state.donation_id}
    if action == 'offer':
        candidate = next((c for c in state.candidates if c.ngo_id == state.proposed_ngo_id), None)
        if candidate is None:
            return {**payload, 'action': 'escalate', 'selected_ngo': None,
                    'reason_code': 'missing_information'}
        return {**payload, 'action': 'propose_offer',
                'selected_ngo': f'NGO {candidate.ngo_id}',
                'reason_code': 'capacity', 'quantity': state.quantity,
                'selected_capacity': candidate.capacity,
                'selected_distance_km': candidate.straight_line_km}
    if action == 'wait':
        return {**payload, 'action': 'wait', 'selected_ngo': None,
                'reason_code': 'pending_offer'}
    if action == 'escalate':
        return {**payload, 'action': 'escalate', 'selected_ngo': None,
                'reason_code': 'no_eligible_ngo'}
    return {**payload, 'action': 'stop', 'selected_ngo': None,
            'reason_code': 'expired' if state.donation_status == 'expired'
            else 'missing_information'}


def local_fallback(payload: dict) -> str:
    action = payload['action']
    if action == 'propose_offer':
        return (f"{payload['selected_ngo']} is a candidate identified by the backend. "
                'Eligibility must be rechecked before creating an offer.')
    if action == 'wait':
        return 'An NGO offer is pending. Wait for a response or timeout.'
    if action == 'stop':
        return 'This donation is not available for additional matching.'
    return 'The agent could not confirm a suitable match. Administrator review is required.'


def get_explanation(payload: dict, *, timeout: float = 1.5) -> dict:
    """Query optional service; never trust it to override a T3 decision."""
    fallback = {
        'donation_id': payload['donation_id'], 'action': payload['action'],
        'selected_ngo': payload['selected_ngo'],
        'explanation': local_fallback(payload),
        'source': 'backend_fallback', 'model_used': False,
    }
    if os.getenv('ANNSETU_EXPLANATIONS_ENABLED', 'false').lower() != 'true':
        return fallback
    address = os.getenv('ANNSETU_ML_SERVICE_URL', 'http://127.0.0.1:8100/v1/explain')
    # Explicitly limit the default local integration to loopback. Remote GPU
    # deployment requires a separately reviewed private/authenticated transport.
    if address not in ('http://127.0.0.1:8100/v1/explain', 'http://localhost:8100/v1/explain'):
        return fallback
    headers = {'Content-Type': 'application/json'}
    secret = os.getenv('ANNSETU_SERVICE_KEY', '')
    if secret:
        headers['X-Service-Key'] = secret
    request = Request(address, data=json.dumps(payload).encode('utf-8'),
                      headers=headers, method='POST')
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return fallback
            data = json.loads(response.read(8192).decode('utf-8'))
        if (not isinstance(data, dict)
                or data.get('donation_id') != payload['donation_id']
                or data.get('action') != payload['action']
                or data.get('selected_ngo') != payload['selected_ngo']
                or data.get('source') not in ('model', 'fallback')
                or type(data.get('model_used')) is not bool
                or (data['model_used'] != (data['source'] == 'model'))
                or not isinstance(data.get('explanation'), str)
                or not 10 <= len(data['explanation']) <= 400):
            return fallback
        return {k: data[k] for k in fallback.keys()}
    except (OSError, URLError, HTTPError, TimeoutError, ValueError, UnicodeError):
        return fallback

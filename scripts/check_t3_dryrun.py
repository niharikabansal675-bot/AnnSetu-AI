"""Read-only T3+ML integration check. Optional secret via environment variable.

Run with backend on :8000. Never prints tokens or personal data.
"""
import json
import os
import urllib.error
import urllib.request

id_text = os.getenv('ANNSETU_TEST_DONATION_ID', '9')
if not id_text.isdecimal() or int(id_text) < 1:
    raise SystemExit('Set ANNSETU_TEST_DONATION_ID to an existing positive donation ID')
token = os.getenv('ANNSETU_ADMIN_JWT', '')
if not token:
    raise SystemExit('Set ANNSETU_ADMIN_JWT privately in your terminal (not in a file or Git).')
url = f'http://127.0.0.1:8000/api/admin/t3/explain/{id_text}?include_road=false'
request = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
try:
    with urllib.request.urlopen(request, timeout=10) as response:
        body = json.load(response)
except urllib.error.HTTPError as exc:
    raise SystemExit(f'Backend returned HTTP {exc.code} (check admin login/donation ID)') from None
except urllib.error.URLError:
    raise SystemExit('Backend unavailable at 127.0.0.1:8000') from None
assert body['mode'] == 'dry_run' and body['writes_enabled'] is False
assert body['offer_created'] is False
assert body['explanation']['action'] == body['decision']['action']
assert body['explanation']['selected_ngo'] == body['decision']['selected_ngo']
print(json.dumps({'http': 200, 'mode': body['mode'], 'action': body['decision']['action'],
                  'explanation_source': body['explanation']['source'],
                  'model_used': body['explanation']['model_used'],
                  'writes_enabled': body['writes_enabled'],
                  'offer_created': body['offer_created']}, indent=2))

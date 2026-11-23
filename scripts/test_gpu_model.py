"""Run on GPU host after starting model service; obtains key from environment."""
import json, os, urllib.request
key=os.environ.get('ANNSETU_SERVICE_KEY')
if not key: raise SystemExit('Set ANNSETU_SERVICE_KEY in your private environment; do not paste it into code')
payload={'donation_id': 999, 'action': 'stop', 'selected_ngo': None, 'reason_code':'expired'}
request=urllib.request.Request('http://127.0.0.1:8100/v1/explain',data=json.dumps(payload).encode(),method='POST',headers={'Content-Type':'application/json','X-Service-Key':key})
with urllib.request.urlopen(request,timeout=120) as response:
    result=json.load(response)
assert result['action']=='stop' and result['selected_ngo'] is None
print('ML output:', json.dumps({k:result[k] for k in ['action','source','model_used','explanation']},indent=2))
if not result['model_used']:
    print('WARNING: model output not used (fallback). See service logs and validator; do not claim GPU inference succeeded.')

"""Full-stack API integration tests on isolated temporary SQLite; safe for PostgreSQL."""
from datetime import datetime, timedelta, timezone
from test_auth import client, register, admin_token


def headers(token):
    return {'Authorization': f'Bearer {token}'}


def verified_user(client, role, email, locality='Indirapuram', capacity=150):
    result=client.post('/api/auth/register',json={
        'name':f'Test {role}', 'email':email, 'password':'TestPass123!',
        'organisation':f'Fictional {role} {email}', 'role':role,
        'locality':locality, 'capacity':capacity if role=='ngo' else 0})
    assert result.status_code==201,result.text
    data=result.json()
    r=client.patch(f"/api/admin/users/{data['user']['id']}/verify",json={'verified':True},headers=headers(admin_token(client)))
    assert r.status_code==200,r.text
    return data


def create_listing(client,provider,quantity=40):
    now=datetime.now(timezone.utc)
    r=client.post('/api/donations',json={
        'title':'Confirmed vegetarian surplus food','food_type':'Vegetarian meals',
        'quantity':quantity,'locality':'Indirapuram','address':'Demonstration location, Ghaziabad',
        'prepared_at':(now-timedelta(minutes=10)).isoformat(),
        'storage':'Covered and stored safely',
        'deadline':(now+timedelta(hours=3)).isoformat()},headers=headers(provider['token']))
    assert r.status_code==201,r.text
    return r.json()


def test_complete_provider_agent_ngo_journey(client):
    provider=verified_user(client,'provider','provider@example.com')
    ngo=verified_user(client,'ngo','ngo@example.com')
    d=create_listing(client,provider)
    offer_run=client.post('/api/agent/run',headers=headers(provider['token']))
    assert offer_run.status_code==200,offer_run.text
    assert len(offer_run.json()['created'])==1
    offer=client.get('/api/offers',headers=headers(ngo['token'])).json()[0]
    assert offer['donation_id']==d['id']
    accept=client.post(f"/api/offers/{offer['id']}/respond",json={'decision':'accept'},headers=headers(ngo['token']))
    assert accept.status_code==200,accept.text
    qr=client.get(f"/api/donations/{d['id']}/qr",headers=headers(provider['token']))
    assert qr.status_code==200 and qr.headers['content-type']=='image/png'
    from main import Donation
    # Read only from the isolated test database; real users scan a QR instead.
    from main import db_session
    session=next(iter(client.app.dependency_overrides[db_session]()))
    token=session.get(Donation,d['id']).qr_token
    bad=client.post(f"/api/donations/{d['id']}/pickup",json={'token':'invalid'},headers=headers(ngo['token']))
    assert bad.status_code==403
    pickup=client.post(f"/api/donations/{d['id']}/pickup",json={'token':token},headers=headers(ngo['token']))
    assert pickup.status_code==200
    repeat=client.post(f"/api/donations/{d['id']}/pickup",json={'token':token},headers=headers(ngo['token']))
    assert repeat.status_code==409
    complete=client.post(f"/api/donations/{d['id']}/complete",headers=headers(ngo['token']))
    assert complete.status_code==200
    again=client.post(f"/api/donations/{d['id']}/complete",headers=headers(ngo['token']))
    assert again.status_code==409
    tracking=client.get(f"/api/donations/{d['id']}/tracking",headers=headers(provider['token']))
    assert tracking.status_code==200
    actions=[x['action'] for x in tracking.json()['events']]
    assert 'listing_created' in actions and 'offer_created' in actions and 'picked_up' in actions and 'completed' in actions
    reports=client.get('/api/reports',headers=headers(admin_token(client)))
    assert reports.status_code==200
    assert reports.json()['completed_quantity']==d['quantity']
    assert reports.json()['donations_by_status']['completed']==1
    assert client.get('/api/reports',headers=headers(ngo['token'])).status_code==403


def test_edit_and_cancel_listing(client):
    provider=verified_user(client,'provider','editor@example.com')
    d=create_listing(client,provider)
    new_deadline=(datetime.now(timezone.utc)+timedelta(hours=4)).isoformat()
    edited=client.patch(f"/api/donations/{d['id']}",json={'title':'Updated confirmed meals','quantity':50,'storage':'Chilled containers','deadline':new_deadline},headers=headers(provider['token']))
    assert edited.status_code==200,edited.text
    assert edited.json()['quantity']==50
    cancel=client.post(f"/api/donations/{d['id']}/cancel",json={'reason':'Event organiser withdrew listing'},headers=headers(provider['token']))
    assert cancel.status_code==200
    assert cancel.json()['status']=='cancelled'
    assert client.post(f"/api/donations/{d['id']}/cancel",json={'reason':'Repeated attempt'},headers=headers(provider['token'])).status_code==409


def test_agent_decline_and_reassignment(client):
    provider=verified_user(client,'provider','p2@example.com')
    ngo1=verified_user(client,'ngo','ngo1@example.com',locality='Indirapuram')
    ngo2=verified_user(client,'ngo','ngo2@example.com',locality='Vaishali')
    d=create_listing(client,provider)
    run=client.post('/api/agent/run',headers=headers(provider['token']))
    assert len(run.json()['created'])==1
    first=client.get('/api/offers',headers=headers(ngo1['token'])).json()[0]
    assert client.post(f"/api/offers/{first['id']}/respond",headers=headers(ngo1['token']),json={'decision':'decline'}).status_code==200
    again=client.post('/api/agent/run',headers=headers(provider['token']))
    assert len(again.json()['created'])==1
    second=client.get('/api/offers',headers=headers(ngo2['token'])).json()[0]
    assert second['donation_id']==d['id']
    assert client.post(f"/api/offers/{second['id']}/respond",headers=headers(ngo2['token']),json={'decision':'accept'}).status_code==200
    # Second run must not assign a donation accepted already.
    assert client.post('/api/agent/run',headers=headers(provider['token'])).json()['created']==[]


def test_no_eligible_ngo_escalates(client):
    provider=verified_user(client,'provider','p3@example.com')
    d=create_listing(client,provider,quantity=9999)
    r=client.post('/api/agent/run',headers=headers(provider['token']))
    assert d['id'] in r.json()['escalated']
    history=client.get(f"/api/donations/{d['id']}/tracking",headers=headers(provider['token'])).json()['events']
    assert any(e['action']=='escalation' for e in history)

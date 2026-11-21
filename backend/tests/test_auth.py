"""Milestone 2: isolated authentication + verification evidence tests.

Uses a temporary in-memory SQLite database, never the real PostgreSQL database.
"""
import os
import sys
from pathlib import Path

# Set env before importing main, so importing app cannot reach the real database.
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET'] = 'only-for-local-pytest-tests-not-for-production'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://127.0.0.1:3000'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from main import Base, User, app, db_session, password_hash

@pytest.fixture
def client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(name='Test Administrator', email='admin@example.com', password_hash=password_hash('AdminPass123!'), role='admin', organisation='Food Rescue', locality='Ghaziabad', verified=True))
        db.commit()

    def isolated_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[db_session] = isolated_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register(client, email='ngo@example.com', role='ngo'):
    return client.post('/api/auth/register', json={
        'name': 'Test User', 'email': email, 'password': 'TestingPass123!',
        'role': role, 'organisation': 'SIMULATION NGO' if role == 'ngo' else 'SIMULATION CATERER',
        'locality': 'Indirapuram', 'capacity': 100 if role == 'ngo' else 0,
    })


def admin_token(client):
    result = client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPass123!'})
    assert result.status_code == 200
    return result.json()['token']


def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_frontend_cors_preflight(client):
    r = client.options('/api/auth/register', headers={
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    assert r.status_code == 200
    assert r.headers.get('access-control-allow-origin') == 'http://localhost:3000'


def test_register_creates_unverified_account(client):
    r = register(client)
    assert r.status_code == 201, r.text
    u = r.json()['user']
    assert u['email'] == 'ngo@example.com'
    assert u['role'] == 'ngo'
    assert u['verified'] is False
    assert 'password_hash' not in u


def test_duplicate_email_is_rejected(client):
    assert register(client).status_code == 201
    r = register(client)
    assert r.status_code == 409


def test_wrong_password_is_rejected(client):
    assert register(client).status_code == 201
    r = client.post('/api/auth/login', json={'email': 'ngo@example.com', 'password': 'wrong-password'})
    assert r.status_code == 401


def test_non_admin_cannot_verify(client):
    account = register(client).json()
    token = account['token']
    r = client.patch(f"/api/admin/users/{account['user']['id']}/verify", json={'verified': True}, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 403


def test_admin_can_verify_and_user_sees_update(client):
    account = register(client).json()
    admin = admin_token(client)
    r = client.patch(f"/api/admin/users/{account['user']['id']}/verify", json={'verified': True}, headers={'Authorization': f'Bearer {admin}'})
    assert r.status_code == 200, r.text
    assert r.json()['verified'] is True
    me = client.get('/api/me', headers={'Authorization': f"Bearer {account['token']}"})
    assert me.status_code == 200
    assert me.json()['verified'] is True


def test_unverified_provider_cannot_post_donation(client):
    account = register(client, 'provider@example.com', 'provider').json()
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    r = client.post('/api/donations', headers={'Authorization': f"Bearer {account['token']}"}, json={
        'title': 'Test confirmed surplus', 'food_type': 'Vegetarian meals',
        'quantity': 40, 'locality': 'Indirapuram', 'address': 'Demo street, Ghaziabad',
        'prepared_at': (now-timedelta(minutes=10)).isoformat(),
        'storage': 'Covered container', 'deadline': (now+timedelta(hours=2)).isoformat(),
    })
    assert r.status_code == 403


def test_cors_both_localhost_and_127_0_0_1(client):
    for origin in ('http://localhost:3000', 'http://127.0.0.1:3000'):
        response = client.options('/api/auth/register', headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        })
        assert response.status_code == 200, response.text
        assert response.headers['access-control-allow-origin'] == origin

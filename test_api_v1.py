from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_all():
    r = client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'demo'})
    assert r.status_code == 200, r.text
    token = r.json()['access_token']
    print('LOGIN OK:', token[:25] + '...')

    r_me = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert r_me.status_code == 200, r_me.text
    print('AUTH ME OK:', r_me.json()['role'])

    r_tickets = client.get('/api/v1/tickets')
    assert r_tickets.status_code == 200, r_tickets.text
    print('TICKETS OK:', r_tickets.json()['total'])

    r_explain = client.post('/api/v1/ai/explain/1')
    assert r_explain.status_code == 200, r_explain.text
    print('AI EXPLAIN OK:', r_explain.json()['mitre_technique'])

    r_sys = client.get('/api/v1/health/system')
    assert r_sys.status_code == 200, r_sys.text
    print('HEALTH SYSTEM OK:', r_sys.json()['database_engine'])

if __name__ == '__main__':
    test_all()
    print('ALL TESTS PASSED!')


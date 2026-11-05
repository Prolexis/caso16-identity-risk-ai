from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
for path in ['/api/v1/health', '/api/v1/dashboard', '/api/v1/accounts', '/api/v1/findings']:
    response = client.get(path)
    print(path, response.status_code, response.text[:180])
response = client.post('/api/v1/scans', json={'actor': 'test@demo.local', 'role': 'Analista de ciberseguridad'})
print('/api/v1/scans', response.status_code, response.json())

from streamlit.testing.v1 import AppTest
at = AppTest.from_file('app.py', default_timeout=30)
at.run()
print('ui_run', len(at.exception), len(at.title), len(at.text_input), len(at.button))
print('ui_errors', [str(x.value) for x in at.exception])

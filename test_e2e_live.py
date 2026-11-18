import urllib.request
import json
import time

payload = json.dumps({
    'run_m1': True,
    'run_m2': True,
    'run_m3': True,
    'use_optuna': True,
    'optuna_trials_m1': 3,
    'optuna_trials_m2': 3,
    'use_demo_dataset': False,
}).encode()

req = urllib.request.Request(
    'http://127.0.0.1:8001/api/v1/training/start',
    data=payload,
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req)
job = json.loads(res.read().decode())
job_id = job['job_id']
print('Job iniciado:', job_id)

for i in range(40):
    time.sleep(1)
    status_res = urllib.request.urlopen(f'http://127.0.0.1:8001/api/v1/training/jobs/{job_id}')
    status_data = json.loads(status_res.read().decode())
    st = status_data.get('status')
    pct = status_data.get('progress', {}).get('percent')
    msg = status_data.get('progress', {}).get('message')
    print(f'[{i+1}s] Estado: {st} ({pct}%) - {msg}')
    if st in ('completed', 'failed', 'cancelled'):
        if st == 'completed':
            res_obj = status_data.get('result', {})
            print('M1 test accuracy:', res_obj.get('models', {}).get('M1_RandomForest', {}).get('test_metrics', {}).get('accuracy'))
            print('M2 test accuracy:', res_obj.get('models', {}).get('M2_XGBoost', {}).get('test_metrics', {}).get('accuracy'))
            print('M3 anomalias detectadas:', res_obj.get('models', {}).get('M3_IsolationForest', {}).get('anomalies_detected'))
            print('Comparativa:', res_obj.get('comparison_table', [])[:2])
            print('Graficos generados:', list(res_obj.get('charts', {}).keys()))

            # Probar descarga de reportes
            for fmt in ['pdf', 'docx', 'xlsx']:
                rep_url = f'http://127.0.0.1:8001/api/v1/training/jobs/{job_id}/report?format={fmt}'
                rep_res = urllib.request.urlopen(rep_url)
                body = rep_res.read()
                print(f'Reporte {fmt.upper()} descargado correctamente: {len(body)} bytes')
        break

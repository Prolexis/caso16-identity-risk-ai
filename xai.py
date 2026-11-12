"""Faithful explanations of the existing deterministic score (not fabricated SHAP)."""
from datetime import date, datetime, timezone
import hashlib
import json

MODEL_VERSION = 'deterministic-r01-r06-v1'

def dataset_hash(rows):
    ordered = sorted(rows, key=lambda r: str(r.get('external_id', r.get('id', ''))))
    return hashlib.sha256(json.dumps(ordered, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()

def explain_account(row):
    import data_layer as dl
    last = row.get('last_activity')
    if isinstance(last, str):
        last = date.fromisoformat(last[:10])
    review = row.get('review_at')
    if isinstance(review, str):
        review = date.fromisoformat(review[:10])
    outside = [r.strip() for r in str(row.get('privileged_roles') or '').split('|') if r.strip() and r.strip() not in dl.ALLOWED_PRIVILEGES]
    parts = {'R01': 30 if last is None else min(30, max(0, (date.today()-last).days//5)),
             'R02': 25 if row.get('is_admin') else 0, 'R03': 0,
             'R04': (20 if row.get('account_type') == 'service' else 0) + (15 if row.get('password_never_expires') else 0),
             'R05': 25 if outside else 0, 'R06': 10 if review is None else 0}
    raw = sum(parts.values())
    score = dl.compute_score(row)
    triggered = []
    if last is None or (date.today()-last).days >= 90: triggered.append('R01')
    if row.get('is_admin') and not row.get('justification_verified'): triggered.append('R02')
    if row.get('is_admin') and row.get('is_duplicate'): triggered.append('R03')
    if row.get('account_type') == 'service' and row.get('password_never_expires'): triggered.append('R04')
    if outside: triggered.append('R05')
    if score >= 60 and (review is None or (date.today()-review).days > 90): triggered.append('R06')
    contributions = [{'rule': k, 'raw_points': v, 'points': v * score/raw if raw else 0} for k,v in parts.items()]
    return {'score': score, 'severity': dl.classify_risk(score), 'triggered_rules': triggered,
            'contributions': contributions, 'raw_score': raw, 'cap_adjustment': score-raw,
            'interpretation': 'El score pondera atributos, no el número de reglas disparadas. R03 no agrega puntos. Las contribuciones se escalan proporcionalmente al límite 100; no son SHAP.',
            'model_version': MODEL_VERSION, 'dataset_hash': dataset_hash([row]),
            'timestamp': datetime.now(timezone.utc).isoformat(), 'grad_cam': 'No aplica: datos tabulares, no imágenes.',
            'mitre_attack': 'T1078.002; T1098; T1558.003', 'iso27001_control': 'ISO/IEC 27001:2022 A.5.16, A.5.18, A.8.2'}

def ablate_account(row):
    baseline = explain_account(row)['score']
    return [{'attribute': key, 'score': explain_account(dict(row, **{key: value}))['score'],
             'baseline': baseline, 'interpretation': 'Contrafactual heurístico, no efecto causal.'}
            for key,value in {'is_admin':False, 'password_never_expires':False, 'privileged_roles':'Domain Users', 'last_activity':date.today(), 'review_at':date.today()}.items()]

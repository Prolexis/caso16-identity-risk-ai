"""Validated CSV/JSON ingestion; rejects invalid rows without deleting existing data."""
import csv
import io
import json
import re
from datetime import date, datetime, timezone

BOOL_FIELDS = ('active','is_admin','justification_verified','is_duplicate','password_never_expires')

def validate_records(rows):
    accepted, rejected, seen = [], [], set()
    for index, original in enumerate(rows, 1):
        try:
            if not isinstance(original, dict): raise ValueError('La fila debe ser un objeto')
            row = dict(original)
            for key in ('external_id','username','source'):
                if not isinstance(row.get(key), str) or not row[key].strip(): raise ValueError(f'{key} obligatorio')
                if len(row[key]) > (80 if key == 'source' else 120): raise ValueError(f'{key} demasiado largo')
            if row['external_id'] in seen: raise ValueError('external_id duplicado en archivo')
            domain = row.get('domain') or (re.search(r'\(([^)]+)\)', row['source']).group(1) if re.search(r'\(([^)]+)\)', row['source']) else '')
            if domain and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z0-9.-]+', domain): raise ValueError('Dominio inválido')
            row['account_type'] = row.get('account_type') or 'user'
            if row['account_type'] not in ('user','admin','service'): raise ValueError('account_type inválido')
            for key in BOOL_FIELDS:
                value = row.get(key, key == 'active')
                if isinstance(value, str): value = value.strip().lower()
                if value in (True, 1, 'true','1'): row[key] = True
                elif value in (False, 0, 'false','0'): row[key] = False
                else: raise ValueError(f'{key} requiere booleano')
            for key in ('last_activity','review_at'):
                value = row.get(key)
                row[key] = date.fromisoformat(str(value)[:10]) if value not in (None,'') else None
                if row[key] and row[key] > date.today(): raise ValueError(f'{key} no puede ser futura')
            result = {key:row[key] for key in ('external_id','username','source','account_type',*BOOL_FIELDS,'last_activity','review_at')}
            result.update(display_name=str(row.get('display_name') or row['username'])[:180], email=str(row.get('email') or '')[:180], privileged_roles=str(row.get('privileged_roles') or 'Domain Users'), created_at=datetime.now(timezone.utc), risk_score=0)
            accepted.append(result)
            seen.add(row['external_id'])
        except (ValueError, TypeError) as exc:
            rejected.append({'row':index,'reason':str(exc)})
    return {'accepted':accepted,'rejected':rejected}

def parse_upload(content, format):
    if len(content.encode('utf-8')) > 5_000_000: raise ValueError('Límite: 5 MB')
    if format == 'csv': rows = list(csv.DictReader(io.StringIO(content.lstrip('\ufeff'))))
    elif format == 'json':
        rows = json.loads(content)
        if isinstance(rows, dict): rows = rows.get('data', [])
    else: raise ValueError('Formato permitido: csv o json normalizado')
    if not isinstance(rows, list) or len(rows) > 10000: raise ValueError('Se requiere lista de hasta 10000 cuentas normalizadas')
    return validate_records(rows)

def import_accounts(content, format, actor, role):
    import data_layer as dl
    from sqlalchemy import select, insert
    dl.require_permission(role, 'policies')
    report = parse_upload(content, format)
    added = skipped = 0
    with dl.engine.begin() as conn:
        for row in report.pop('accepted'):
            exists = conn.execute(select(dl.accounts.c.id).where(dl.accounts.c.external_id == row['external_id'])).first()
            if exists: skipped += 1; continue
            row['risk_score'] = dl.compute_score(row)
            conn.execute(insert(dl.accounts).values(**row)); added += 1
        dl.audit_event(conn, actor, role, 'import_accounts', 'directory_accounts', 'success', f'inserted={added}; existing={skipped}; rejected={len(report["rejected"])}')
    return dict(report, inserted=added, skipped=skipped)

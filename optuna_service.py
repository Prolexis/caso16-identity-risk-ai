"""Persistent SQLAlchemy jobs/presets with a bounded in-process worker.

SQLite/PostgreSQL supported. Pending jobs survive restart and can be resumed explicitly;
this is not a distributed queue. HTTP layer must enforce RBAC and audit mutations.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import json
import threading
import uuid
from sqlalchemy import MetaData, Table, Column, String, Text, select, insert, update, delete
from ml_engine import TrainingConfig, train_model

metadata=MetaData()
jobs=Table('ml_training_jobs',metadata,Column('id',String(40),primary_key=True),Column('actor',String(160),nullable=False),Column('status',String(30),nullable=False),Column('config',Text,nullable=False),Column('rows',Text,nullable=False),Column('progress',Text,nullable=False),Column('result',Text),Column('error',Text),Column('created_at',String(40),nullable=False),Column('updated_at',String(40),nullable=False))
presets=Table('ml_search_presets',metadata,Column('id',String(40),primary_key=True),Column('actor',String(160),nullable=False),Column('name',String(120),nullable=False),Column('config',Text,nullable=False),Column('updated_at',String(40),nullable=False))
# Study summaries alongside native Optuna RDB tables (studies/trials/etc.).
studies=Table('optuna_studies',metadata,Column('name',String(160),primary_key=True),Column('job_id',String(40),nullable=False),Column('payload',Text,nullable=False))
_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='caso16-training')
_active=set()
_lock=threading.Lock()


def _engine(engine=None):
    if engine is None:
        from data_layer import engine
    metadata.create_all(engine)
    return engine


def _now(): return datetime.now(timezone.utc).isoformat()
def _dump(value): return json.dumps(value,default=str,ensure_ascii=False,allow_nan=False)


def _decode(row):
    result=dict(row)
    result.pop('rows',None)
    for key in ('config','progress','result','payload'):
        if key in result and result[key] is not None:
            result[key]=json.loads(result[key])
    return result


def _patch(engine,job_id,**values):
    values['updated_at']=_now()
    for key in ('progress','result'):
        if key in values: values[key]=_dump(values[key])
    with engine.begin() as conn:
        conn.execute(update(jobs).where(jobs.c.id==job_id).values(**values))


def _run(engine,job_id):
    try:
        with engine.begin() as conn:
            claimed=conn.execute(update(jobs).where(jobs.c.id==job_id,jobs.c.status=='pending').values(status='running',updated_at=_now()))
            if claimed.rowcount!=1: return
            row=dict(conn.execute(select(jobs).where(jobs.c.id==job_id)).mappings().one())
        url=engine.url.render_as_string(hide_password=False)
        # Native Optuna cannot share a SQLAlchemy in-memory DB; retain trials in job JSON there.
        storage=None if engine.url.get_backend_name()=='sqlite' and engine.url.database in (None,'',':memory:') else url
        result=train_model(json.loads(row['rows']),json.loads(row['config']),progress=lambda p:_patch(engine,job_id,progress=p),storage_url=storage)
        with engine.begin() as conn:
            for study in result['studies']:
                conn.execute(insert(studies).values(name=study['name'],job_id=job_id,payload=_dump(study)))
        _patch(engine,job_id,status='completed',result=result,progress={'stage':'completed'},error=None)
    except Exception as exc:
        _patch(engine,job_id,status='failed',error=f'{type(exc).__name__}: {exc}',progress={'stage':'failed'})
    finally:
        with _lock: _active.discard(job_id)


def submit_training(rows,config=None,actor='system',engine=None):
    cfg=config if isinstance(config,TrainingConfig) else TrainingConfig(**(config or {}))
    if not rows: raise ValueError('No hay cuentas para entrenar')
    engine=_engine(engine)
    job_id=uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(insert(jobs).values(id=job_id,actor=actor,status='pending',config=_dump(asdict(cfg)),rows=_dump(rows),progress='{}',created_at=_now(),updated_at=_now()))
    with _lock: _active.add(job_id)
    _executor.submit(_run,engine,job_id)
    return get_job(job_id,engine)


def run_training_sync(rows,config=None,actor='system',engine=None):
    """CLI/test helper with identical persistence, no thread race."""
    cfg=config if isinstance(config,TrainingConfig) else TrainingConfig(**(config or {}))
    engine=_engine(engine); job_id=uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(insert(jobs).values(id=job_id,actor=actor,status='pending',config=_dump(asdict(cfg)),rows=_dump(rows),progress='{}',created_at=_now(),updated_at=_now()))
    _run(engine,job_id)
    return get_job(job_id,engine)


def get_job(job_id,engine=None):
    engine=_engine(engine)
    with engine.connect() as conn:
        row=conn.execute(select(jobs).where(jobs.c.id==job_id)).mappings().first()
    return _decode(row) if row else None


def list_jobs(engine=None):
    engine=_engine(engine)
    with engine.connect() as conn:
        return [_decode(r) for r in conn.execute(select(jobs).order_by(jobs.c.created_at.desc())).mappings()]


def get_evaluation(job_id,engine=None):
    job=get_job(job_id,engine)
    return {'job_id':job_id,**job['result']} if job and job['status']=='completed' else None


def list_evaluations(engine=None):
    return [{'job_id':job['id'],**job['result']} for job in list_jobs(engine) if job['status']=='completed']


def list_studies(engine=None):
    engine=_engine(engine)
    with engine.connect() as conn:
        return [_decode(r) for r in conn.execute(select(studies)).mappings()]


def resume_pending(engine=None):
    """Resume queued jobs after restart; stale running jobs are not silently retrained.

Operator can inspect failed/running jobs and explicitly submit a new training request.
"""
    engine=_engine(engine)
    resumed=[]
    for job in list_jobs(engine):
        with _lock:
            if job['status']!='pending' or job['id'] in _active: continue
            _active.add(job['id'])
        _executor.submit(_run,engine,job['id']); resumed.append(job['id'])
    return resumed


def list_presets(actor,engine=None):
    engine=_engine(engine)
    with engine.connect() as conn:
        return [_decode(r) for r in conn.execute(select(presets).where(presets.c.actor==actor)).mappings()]


def save_preset(actor,name,config,preset_id=None,engine=None):
    cfg=config if isinstance(config,TrainingConfig) else TrainingConfig(**config)
    name=name.strip()
    if not name or len(name)>120: raise ValueError('Nombre de preset requiere 1–120 caracteres')
    engine=_engine(engine)
    with engine.begin() as conn:
        if preset_id:
            exists=conn.execute(select(presets.c.id).where(presets.c.id==preset_id,presets.c.actor==actor)).first()
            if not exists: raise ValueError('Preset no existe para este usuario')
            conn.execute(update(presets).where(presets.c.id==preset_id,presets.c.actor==actor).values(name=name,config=_dump(asdict(cfg)),updated_at=_now()))
        else:
            preset_id=uuid.uuid4().hex
            conn.execute(insert(presets).values(id=preset_id,actor=actor,name=name,config=_dump(asdict(cfg)),updated_at=_now()))
    return next(p for p in list_presets(actor,engine) if p['id']==preset_id)


def delete_preset(actor,preset_id,engine=None):
    engine=_engine(engine)
    with engine.begin() as conn:
        deleted=conn.execute(delete(presets).where(presets.c.id==preset_id,presets.c.actor==actor)).rowcount
    return bool(deleted)

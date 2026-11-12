"""Versioned endpoints for data and optional ML; mutations use authenticated roles."""
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
import data_layer as dl

class MetadataUpdate(BaseModel):
    justification_verified: bool | None = None
    review_at: date | None = None
    privilege_justification: str = Field(default='', max_length=800)

class Upload(BaseModel):
    content: str = Field(max_length=5_000_000)
    format: Literal['csv','json']

class Prediction(BaseModel):
    account_id: int | None = None
    attributes: dict | None = None
    model_id: str | None = None

class Preset(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    config: dict

def make_router(authenticated_user):
    router = APIRouter(prefix='/api/v1')
    def audit(user, action, resource):
        with dl.engine.begin() as conn:
            dl.audit_event(conn,user['email'],user['role'],action,resource,'success','Operación autenticada')

    @router.patch('/accounts/{account_id}/metadata')
    def metadata(account_id:int, payload:MetadataUpdate, user=Depends(authenticated_user)):
        changes=payload.model_dump(exclude_unset=True)
        if changes.get('justification_verified', False) is None: raise ValueError('justification_verified no admite null')
        dl.update_account_metadata(account_id,changes,user['email'],user['role'])
        return {'status':'updated','account_id':account_id}

    @router.post('/accounts/import')
    def upload(payload:Upload,user=Depends(authenticated_user)):
        from ingestion import import_accounts
        return import_accounts(payload.content,payload.format,user['email'],user['role'])

    @router.post('/train',status_code=202)
    def train(config:dict,user=Depends(authenticated_user)):
        from optuna_service import submit_training
        dl.require_permission(user['role'],'write')
        result=submit_training(dl.account_frame().to_dict('records'),config,actor=user['email'],engine=dl.engine)
        audit(user,'submit_training',str(result['id']))
        return result

    @router.get('/train')
    def jobs(user=Depends(authenticated_user)):
        from optuna_service import list_jobs
        return {'items':list_jobs(engine=dl.engine)}

    @router.get('/train/{job_id}')
    def job(job_id:str,user=Depends(authenticated_user)):
        from optuna_service import get_job
        result=get_job(job_id,engine=dl.engine)
        if result is None: raise HTTPException(404,'Job no encontrado')
        return result

    @router.get('/evaluation')
    def evaluation(user=Depends(authenticated_user)):
        from optuna_service import list_evaluations
        return {'items':list_evaluations(engine=dl.engine)}

    @router.post('/predict')
    def predict(payload:Prediction,user=Depends(authenticated_user)):
        from ml_engine import predict_account
        if payload.account_id is not None:
            with dl.engine.connect() as conn:
                row=conn.execute(select(dl.accounts).where(dl.accounts.c.id==payload.account_id)).mappings().first()
            if not row: raise HTTPException(404,'Cuenta no encontrada')
            row=dict(row)
        elif payload.attributes is not None:
            from ingestion import validate_records
            fields=dict(external_id='prediction',username='prediction',source='Manual',**{k:v for k,v in payload.attributes.items() if k not in ('external_id','username','source')})
            checked=validate_records([fields])
            if checked['rejected']: raise ValueError(checked['rejected'][0]['reason'])
            row=checked['accepted'][0]
        else: raise ValueError('Indique account_id o attributes')
        result=predict_account(row,model_id=payload.model_id)
        audit(user,'predict',str(payload.account_id or 'attributes'))
        return result

    @router.get('/presets')
    def presets(user=Depends(authenticated_user)):
        from optuna_service import list_presets
        return {'items':list_presets(user['email'],engine=dl.engine)}

    @router.post('/presets',status_code=201)
    def create_preset(payload:Preset,user=Depends(authenticated_user)):
        from optuna_service import save_preset
        dl.require_permission(user['role'],'write')
        result=save_preset(user['email'],payload.name,payload.config,engine=dl.engine)
        audit(user,'create_preset',payload.name)
        return result

    @router.patch('/presets/{preset_id}')
    def edit_preset(preset_id:str,payload:Preset,user=Depends(authenticated_user)):
        from optuna_service import save_preset
        dl.require_permission(user['role'],'write')
        result=save_preset(user['email'],payload.name,payload.config,preset_id=preset_id,engine=dl.engine)
        audit(user,'update_preset',preset_id)
        return result

    @router.delete('/presets/{preset_id}')
    def delete_preset(preset_id:str,user=Depends(authenticated_user)):
        from optuna_service import delete_preset
        dl.require_permission(user['role'],'write')
        delete_preset(user['email'],preset_id,engine=dl.engine)
        audit(user,'delete_preset',preset_id)
        return {'status':'deleted'}
    return router

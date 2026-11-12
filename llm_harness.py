"""Optional bounded LangFlow client. Deterministic evidence is never overwritten."""
import os
import requests

def enrich(output, actor, role):
    import data_layer as dl
    from xai import dataset_hash
    output = dict(output, mode='deterministic', model_version='deterministic-r01-r06-v1', llm_used=False)
    output['dataset_hash'] = dataset_hash(dl.account_frame().to_dict('records'))
    url = os.getenv('LANGFLOW_URL', '').strip()
    if os.getenv('CASO16_LLM_MODE','deterministic') != 'langflow' or not url:
        output['fallback_reason'] = 'Proveedor LLM no configurado'
        return output
    if not url.startswith(('https://','http://')):
        output['fallback_reason'] = 'LANGFLOW_URL inválida'; return output
    try:
        timeout = min(10, max(0.1, float(os.getenv('LANGFLOW_TIMEOUT','3'))))
        retries = min(2, max(0, int(os.getenv('LANGFLOW_RETRIES','1'))))
    except ValueError:
        timeout, retries = 3, 1
    contract = {k:output[k] for k in ('finding_id','rule_id','risk_score','summary','mitre_attack','iso27001_control')}
    for attempt in range(retries+1):
        outcome='fallback'
        try:
            response=requests.post(url,json={'input_value':str(contract),'input_type':'chat','output_type':'chat'},headers={'x-api-key':os.getenv('LANGFLOW_API_KEY','')},timeout=timeout)
            response.raise_for_status()
            # Explicit structured output contract: reject arbitrary text that may contradict score.
            candidate=response.json().get('caso16_explanation',{})
            if candidate.get('risk_score') != output['risk_score'] or candidate.get('rule_id') != output['rule_id']:
                raise ValueError('Respuesta no respeta contrato determinista')
            # LLM may select approved follow-up IDs only; no unverified generated factual claims.
            catalog={'review':'Revisar evidencia con el propietario de la cuenta.','recertify':'Recertificar privilegios mediante aprobación formal.','ticket':'Crear ticket y comprobar la remediación.'}
            choices=candidate.get('recommendations',[])
            if not isinstance(choices,list) or not choices or any(x not in catalog for x in choices):
                raise ValueError('Recomendaciones fuera del catálogo aprobado')
            output.update(llm_used=True, mode='llm_assisted', llm_recommendations=[catalog[x] for x in choices], llm_provider='LangFlow (selección restringida; explicación base determinista)')
            outcome='success'
        except (requests.RequestException,ValueError,TypeError,AttributeError):
            output['fallback_reason']='Proveedor no disponible o respuesta fuera del contrato; se conserva explicación determinista'
        finally:
            with dl.engine.begin() as conn:
                dl.audit_event(conn,actor,role,'llm_attempt',f"finding:{output['finding_id']}",outcome,f'attempt={attempt+1}; timeout={timeout}; provider=langflow')
        if outcome == 'success': break
    return output

from datetime import date, timedelta
import json
import numpy as np
import pytest
from sqlalchemy import create_engine
import ml_engine as ml
from evaluation import aggregate_folds, bootstrap_interval, classification_metrics, compare_models, drift_test
import optuna_service as service


def rows_fixture(n=160):
    today=date.today()
    rows=[]
    for i in range(n):
        # Two well-supported deterministic severity classes; source supplies real domain.
        high=i%2==0
        rows.append(dict(id=i,external_id=f'identity-{i}',username=f'user{i}',source='SharpHound AD (TEST.LOCAL)',account_type='service' if high else 'user',active=True,is_admin=high,justification_verified=False,is_duplicate=False,password_never_expires=high,privileged_roles='Administrators' if high else 'Domain Users',last_activity=None if high else today.isoformat(),review_at=None if high else today.isoformat()))
    return rows


def test_features_exclude_targets_and_identifiers():
    rows=rows_fixture(2)
    before=ml.feature_matrix(rows)
    for row in rows:
        row.update(risk_score=999,severity='fabricated',domain='new',id=999,username='secret',rule_R01=10)
    np.testing.assert_equal(before,ml.feature_matrix(rows))
    assert not {'risk_score','severity','domain','username'} & set(ml.FEATURES)


def test_split_disjoint_reproducible_and_explicit_small_error():
    rows=rows_fixture()
    labels=['Crítico' if i%2==0 else 'Bajo' for i in range(len(rows))]
    split=ml.split_dataset(rows,labels)
    assert split==ml.split_dataset(rows,labels)
    parts=[set(v) for v in split.values()]
    assert not parts[0]&parts[1] and not parts[0]&parts[2] and not parts[1]&parts[2]
    assert set.union(*parts)==set(range(len(rows)))
    with pytest.raises(ValueError,match='imposible'):
        ml.split_dataset(rows[:8],labels[:8])


def test_metrics_and_statistics():
    y=['Bajo','Crítico','Bajo','Crítico']
    p=['Bajo','Bajo','Bajo','Crítico']
    metrics=classification_metrics(y,p)
    assert metrics['asymmetric_cost']==5
    assert metrics['roc_auc'] is None
    assert aggregate_folds([metrics,metrics])['f1_macro']['std']==0
    ci=bootstrap_interval(y,p,20)
    assert 0<=ci['low']<=ci['high']<=1
    assert compare_models({'a':[.5,.6,.7],'b':[.5,.6,.7]})['p_value']==1
    assert compare_models({'a':[.5,.6,.7],'b':[.5,.6,.7],'c':[.5,.6,.7]})['p_value']==1
    with pytest.raises(ValueError): drift_test([1,2],[3])


def test_deterministic_fallback_and_traversal():
    from data_layer import compute_score
    row=rows_fixture(2)[0]
    result=ml.predict_account(row)
    assert result['score']==compute_score(row)
    assert result['mode']=='deterministic' and result['ml'] is None
    assert 'R05' in result['triggered_rules']
    with pytest.raises(ValueError): ml.predict_account(row,'../../untrusted')
    result=ml.predict_account(row,'0'*32)
    assert result['mode']=='deterministic' and result['fallback_reason']


def test_presets_ownership_and_config(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'jobs.db'))
    p=service.save_preset('alice','baseline',{},engine=engine)
    assert service.list_presets('bob',engine)==[]
    assert not service.delete_preset('bob',p['id'],engine)
    with pytest.raises(ValueError): service.save_preset('bob','stolen',{},p['id'],engine)
    assert service.delete_preset('alice',p['id'],engine)
    with pytest.raises(ValueError): ml.TrainingConfig(sampler='cmaes')
    with pytest.raises(ValueError): ml.TrainingConfig(n_trials=0)


def test_actual_nested_training_and_persistence(tmp_path,monkeypatch):
    pytest.importorskip('optuna')
    monkeypatch.setattr(ml,'ARTIFACT_DIR',tmp_path/'models')
    engine=create_engine('sqlite:///'+str(tmp_path/'jobs.db'))
    cfg=ml.TrainingConfig(outer_folds=2,inner_folds=2,n_trials=1,bootstrap_resamples=10)
    job=service.run_training_sync(rows_fixture(),cfg,actor='test',engine=engine)
    assert job['status']=='completed',job['error']
    result=job['result']
    assert len(result['folds'])==2 and len(result['studies'])==3
    assert all(len(s['trials'])==1 for s in result['studies'])
    assert service.get_evaluation(job['id'],engine)['model_id']==result['model_id']
    assert len(service.list_studies(engine))==3
    predicted=ml.predict_account(rows_fixture(2)[0],result['model_id'])
    assert predicted['mode']=='ml_second_opinion'
    assert predicted['score']==100
    assert predicted['ml']['probabilities']
    json.dumps(result,allow_nan=False)


def test_failed_job_persists_without_fake_results(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'failed.db'))
    job=service.run_training_sync(rows_fixture(2),dict(outer_folds=2,inner_folds=2,n_trials=1),engine=engine)
    assert job['status']=='failed' and job['error']
    assert job['result'] is None
    assert service.list_evaluations(engine)==[]

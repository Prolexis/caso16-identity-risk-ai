"""Optional, leakage-safe supervised rule-surrogate training; deterministic authority remains.

Models learn rule-derived severities, NOT independently adjudicated security outcomes.
No score, severity, rule output, identity, or domain enters the feature matrix.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import time
import uuid
import numpy as np

ARTIFACT_DIR = Path(os.getenv('CASO16_MODEL_DIR', str(Path(__file__).parent / 'data' / 'models')))
FEATURES = ('active','is_admin','justification_verified','is_duplicate','password_never_expires','service','activity_days','review_days','role_count')

@dataclass
class TrainingConfig:
    model: str = 'logistic'
    outer_folds: int = 5
    inner_folds: int = 3
    n_trials: int = 50
    seed: int = 42
    timeout: float | None = None
    sampler: str = 'tpe'
    pruner: str = 'median'
    bootstrap_resamples: int = 1000
    stratify: str = 'joint'
    search_space: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.model not in ('logistic','random_forest','gradient_boosting','mlp'):
            raise ValueError('Modelo no soportado')
        for name in ('outer_folds','inner_folds','n_trials','bootstrap_resamples'):
            value = getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,int) or value < (1 if name=='n_trials' else 2):
                raise ValueError(f'{name}: entero fuera de rango')
        if self.sampler not in ('tpe','random') or self.pruner not in ('median','hyperband','none'):
            raise ValueError('Sampler/pruner no soportado: TPE/Random y Median/Hyperband/none')
        if self.stratify not in ('joint','severity'):
            raise ValueError('stratify debe ser joint o severity')
        if self.timeout is not None and (not np.isfinite(self.timeout) or self.timeout <= 0):
            raise ValueError('timeout debe ser positivo')
        if not isinstance(self.search_space,dict):
            raise ValueError('search_space debe ser objeto')


def _config(config):
    return config if isinstance(config,TrainingConfig) else TrainingConfig(**(config or {}))


def _days(value, today):
    if value is None or str(value) in ('NaT','nan','None',''):
        return np.nan
    return max(0,(today-date.fromisoformat(str(value)[:10])).days)


def feature_matrix(rows, reference_date=None):
    today = date.fromisoformat(reference_date) if isinstance(reference_date,str) else reference_date or date.today()
    return np.asarray([[float(bool(row.get(k,False))) for k in FEATURES[:5]] +
                       [float(row.get('account_type')=='service'), _days(row.get('last_activity'),today), _days(row.get('review_at'),today), float(len([r for r in str(row.get('privileged_roles') or '').split('|') if r.strip()]))]
                       for row in rows], dtype=float)


def split_dataset(rows, labels, config=None):
    from sklearn.model_selection import train_test_split, StratifiedKFold
    cfg = _config(config)
    idx = np.arange(len(rows))
    def domain(row):
        if row.get('domain'): return str(row['domain'])
        source = str(row.get('source',''))
        if '(' in source and ')' in source: return source.rsplit('(',1)[1].split(')',1)[0]
        username = str(row.get('username',''))
        return username.rsplit('@',1)[1] if '@' in username else 'unknown'
    domains = [domain(r) for r in rows]
    strata = np.asarray([f'{d}::{y}' for d,y in zip(domains,labels)] if cfg.stratify=='joint' else labels)
    try:
        dev, hold = train_test_split(idx,test_size=.30,random_state=cfg.seed,stratify=strata)
        val, test = train_test_split(hold,test_size=.50,random_state=cfg.seed,stratify=strata[hold])
        y = np.asarray(labels)
        # Validate actual partitions, not a misleading global minimum heuristic.
        if min(np.unique(y[dev],return_counts=True)[1]) < cfg.outer_folds:
            raise ValueError('Desarrollo tiene clases menores que outer_folds')
        for tr,_ in StratifiedKFold(cfg.outer_folds,shuffle=True,random_state=cfg.seed).split(dev,y[dev]):
            if min(np.unique(y[dev][tr],return_counts=True)[1]) < cfg.inner_folds:
                raise ValueError('Un outer_train tiene clases menores que inner_folds')
        if any(set(y[x]) != set(y) for x in (dev,val,test)):
            raise ValueError('Una partición pierde clases')
    except ValueError as exc:
        raise ValueError(f'Partición 70/15/15 y CV {cfg.outer_folds}x{cfg.inner_folds} imposible con estos estratos ({cfg.stratify}): {exc}. Añada datos o configure explícitamente menos folds/estratificación severity; no se fabrican resultados.') from exc
    return {"development": dev.tolist(), "validation": val.tolist(), "test": test.tolist()}


def _pipeline(model, params, seed):
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.neural_network import MLPClassifier
    candidates = {'logistic': lambda: LogisticRegression(max_iter=1000,random_state=seed,**params),
                  'random_forest': lambda: RandomForestClassifier(random_state=seed,n_jobs=1,**params),
                  'gradient_boosting': lambda: GradientBoostingClassifier(random_state=seed,**params),
                  'mlp': lambda: MLPClassifier(max_iter=400,random_state=seed,**params)}
    return make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),StandardScaler(),candidates[model]())


def _params(trial,cfg):
    defaults = {'logistic': {'C': {'low':.001,'high':100.,'log':True},'class_weight': {'choices':[None,'balanced']}},
                'random_forest': {'n_estimators': {'low':100,'high':800},'max_depth': {'low':3,'high':12},'min_samples_split': {'low':2,'high':20},'class_weight': {'choices':[None,'balanced']}},
                'gradient_boosting': {'n_estimators': {'low':100,'high':800},'learning_rate': {'low':.01,'high':.3,'log':True},'max_depth': {'low':3,'high':12},'subsample': {'low':.6,'high':1.}},
                'mlp': {'alpha': {'low':.00001,'high':.1,'log':True},'learning_rate_init': {'low':.0001,'high':.01,'log':True}}}[cfg.model]
    if set(cfg.search_space)-set(defaults):
        raise ValueError('Hiperparámetros desconocidos: '+str(set(cfg.search_space)-set(defaults)))
    space = {**defaults,**cfg.search_space}
    result = {}
    for name,spec in space.items():
        if 'choices' in spec:
            result[name] = trial.suggest_categorical(name,spec['choices'])
        elif name in ('n_estimators','max_depth','min_samples_split'):
            result[name] = trial.suggest_int(name,**spec)
        else:
            result[name] = trial.suggest_float(name,**spec)
    return result


def train_model(rows, config=None, progress=None, storage_url=None):
    try:
        import optuna
        import joblib
        from sklearn.model_selection import StratifiedKFold
        from sklearn.metrics import f1_score
    except ImportError as exc:
        raise RuntimeError('Entrenamiento requiere dependencias opcionales scikit-learn y Optuna; inferencia determinista sigue disponible') from exc
    from data_layer import compute_score, classify_risk
    from evaluation import classification_metrics, aggregate_folds, bootstrap_interval
    cfg = _config(config)
    rows = [dict(r) for r in rows]
    if not rows:
        raise ValueError('No hay cuentas para entrenar')
    ids = [r.get('external_id',r.get('id',i)) for i,r in enumerate(rows)]
    if len(set(ids))!=len(ids):
        raise ValueError('Identidades duplicadas: deduplicar antes de particionar para evitar fuga')
    y = np.asarray([classify_risk(compute_score(row)) for row in rows])
    if len(np.unique(y))<2:
        raise ValueError('Entrenamiento requiere al menos dos clases de severidad')
    splits = split_dataset(rows,y,cfg)
    reference_date = date.today().isoformat()
    X = feature_matrix(rows,reference_date)
    dataset_hash = hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()
    model_id = uuid.uuid4().hex
    started = time.monotonic()
    folds, fold_models, studies = [], [], []
    dev = np.asarray(splits['development'])
    def optimize(indices, fold):
        sampler = optuna.samplers.TPESampler(seed=cfg.seed+fold) if cfg.sampler=='tpe' else optuna.samplers.RandomSampler(seed=cfg.seed+fold)
        pruner = {'median':optuna.pruners.MedianPruner,'hyperband':optuna.pruners.HyperbandPruner,'none':optuna.pruners.NopPruner}[cfg.pruner]()
        study = optuna.create_study(direction='maximize',sampler=sampler,pruner=pruner,storage=storage_url,study_name=f'caso16-{model_id}-{fold}')
        def objective(trial):
            params = _params(trial,cfg)
            scores=[]
            inner = StratifiedKFold(cfg.inner_folds,shuffle=True,random_state=cfg.seed+fold)
            for step,(tr,va) in enumerate(inner.split(X[indices],y[indices])):
                fitted = _pipeline(cfg.model,params,cfg.seed).fit(X[indices[tr]],y[indices[tr]])
                scores.append(f1_score(y[indices[va]],fitted.predict(X[indices[va]]),average='macro',zero_division=0))
                trial.report(float(np.mean(scores)),step)
                if trial.should_prune():
                    raise optuna.TrialPruned()
            return float(np.mean(scores))
        def callback(study,trial):
            completed = [t.value for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE]
            if progress:
                progress({'stage':'optimization','fold':fold,'trial':trial.number+1,'total_trials':cfg.n_trials,'best_value':max(completed) if completed else None,'elapsed_seconds':time.monotonic()-started})
        study.optimize(objective,n_trials=cfg.n_trials,timeout=cfg.timeout,callbacks=[callback])
        if not any(t.state==optuna.trial.TrialState.COMPLETE for t in study.trials):
            raise ValueError('Ningún trial completado: no existe mejor modelo')
        trials = [{'number':t.number,'params':t.params,'value':t.value,'state':t.state.name,'duration_seconds':t.duration.total_seconds() if t.duration else None} for t in study.trials]
        importance = {}
        if sum(t.state==optuna.trial.TrialState.COMPLETE for t in study.trials)>1:
            try:
                importance=optuna.importance.get_param_importances(study)
            except (ValueError,RuntimeError):
                pass
        studies.append({'name':study.study_name,'fold':fold,'trials':trials,'importance':importance,'warning':'No se garantiza convergencia; inspeccione trials y dispersión.'})
        return study.best_params,study.study_name
    outer = StratifiedKFold(cfg.outer_folds,shuffle=True,random_state=cfg.seed)
    for fold,(tr,va) in enumerate(outer.split(X[dev],y[dev]),1):
        params,name = optimize(dev[tr],fold)
        model = _pipeline(cfg.model,params,cfg.seed).fit(X[dev[tr]],y[dev[tr]])
        metrics = classification_metrics(y[dev[va]],model.predict(X[dev[va]]),model.predict_proba(X[dev[va]]),model.classes_)
        folds.append({'fold':fold,'metrics':metrics,'best_params':params,'study_name':name,'train_indices':dev[tr].tolist(),'validation_indices':dev[va].tolist()})
        fold_models.append(model)
    # Separate inner search on development: never select hyperparameters from outer/test performance.
    params,_ = optimize(dev,cfg.outer_folds+1)
    final = _pipeline(cfg.model,params,cfg.seed).fit(X[dev],y[dev])
    val,test = np.asarray(splits['validation']),np.asarray(splits['test'])
    validation = classification_metrics(y[val],final.predict(X[val]),final.predict_proba(X[val]),final.classes_)
    pred = final.predict(X[test])
    test_metrics = classification_metrics(y[test],pred,final.predict_proba(X[test]),final.classes_)
    from sklearn.ensemble import IsolationForest
    # OOD fit uses development only and same fitted preprocessing.
    transformed = final[:-1].transform(X[dev])
    ood = IsolationForest(random_state=cfg.seed,contamination='auto').fit(transformed)
    ARTIFACT_DIR.mkdir(parents=True,exist_ok=True)
    artifact = {'model':final,'fold_models':fold_models,'ood':ood,'reference_date':reference_date,'dataset_hash':dataset_hash,'model_id':model_id,'development_features':X[dev]}
    path = ARTIFACT_DIR / (model_id+'.joblib')
    joblib.dump(artifact,path)
    return {'model_id':model_id,'config':asdict(cfg),'dataset_hash':dataset_hash,'reference_date':reference_date,'splits':splits,'split_account_ids':{k:[ids[i] for i in v] for k,v in splits.items()},'folds':folds,'aggregate':aggregate_folds([f['metrics'] for f in folds]),'validation':validation,'test':test_metrics,'bootstrap':bootstrap_interval(y[test],pred,cfg.bootstrap_resamples,cfg.seed),'studies':studies,'best_params':params,'elapsed_seconds':time.monotonic()-started,'interpretation':'Modelo sustituto de etiquetas deterministas; no evidencia independiente de detección. Test reservado hasta evaluación final. Validación informativa, no selección. Preprocesamiento ajustado dentro de cada fold.'}


def predict_account(account, model_id=None, policies=None):
    from data_layer import compute_score, classify_risk, ALLOWED_PRIVILEGES
    row = dict(account)
    score = compute_score(row)
    policies = policies or {}
    high = policies.get('POL-RISK-HIGH-THRESHOLD',60)
    critical = policies.get('POL-RISK-CRITICAL-THRESHOLD',80)
    if not 35 <= high < critical <= 100:
        raise ValueError('Umbrales deben cumplir 35 <= alto < crítico <= 100')
    severity = 'Crítico' if score>=critical else 'Alto' if score>=high else 'Medio' if score>=35 else 'Bajo'
    last,review = _days(row.get('last_activity'),date.today()),_days(row.get('review_at'),date.today())
    rules=[]
    if np.isnan(last) or last>=policies.get('POL-INACTIVITY-DAYS',90): rules.append('R01')
    if row.get('is_admin') and not row.get('justification_verified'): rules.append('R02')
    if row.get('is_admin') and row.get('is_duplicate'): rules.append('R03')
    if row.get('account_type')=='service' and row.get('password_never_expires'): rules.append('R04')
    if any(r.strip() not in ALLOWED_PRIVILEGES for r in str(row.get('privileged_roles') or '').split('|') if r.strip()): rules.append('R05')
    if score>=high and (np.isnan(review) or review>90): rules.append('R06')
    deterministic={'score':score,'severity':severity,'triggered_rules':rules}
    try:
        from xai import explain_account
        deterministic['explanation']=explain_account(row)
    except ImportError:
        deterministic['explanation_status']='Módulo XAI no disponible'
    result={'score':score,'severity':severity,'triggered_rules':rules,'deterministic':deterministic,'mode':'deterministic','ml':None,'fallback_reason':'No se seleccionó un modelo entrenado'}
    if not model_id:
        return result
    if not isinstance(model_id,str) or len(model_id)!=32 or any(c not in '0123456789abcdef' for c in model_id):
        raise ValueError('Identificador de modelo inválido')
    try:
        import joblib
        artifact=joblib.load(ARTIFACT_DIR/(model_id+'.joblib')) # Only trusted server-created artifacts, never uploads.
        model=artifact['model']
        x=feature_matrix([row],date.today())
        probability=model.predict_proba(x)[0]
        fold_prob=np.asarray([m.predict_proba(x)[0] for m in artifact['fold_models']])
        predicted=str(model.predict(x)[0])
        result.update(mode='ml_second_opinion',fallback_reason=None,ml={'model_id':model_id,'severity':predicted,'probabilities':dict(zip(model.classes_.tolist(),probability.tolist())),'fold_probability_std':dict(zip(model.classes_.tolist(),fold_prob.std(axis=0,ddof=1).tolist())),'uncertainty_note':'Dispersión de probabilidades entre folds, no intervalo calibrado de riesgo.','out_of_distribution':bool(artifact['ood'].predict(model[:-1].transform(x))[0]==-1),'disagreement':predicted!=severity,'explanation':'Segunda opinión; cualquier discrepancia conserva score/reglas deterministas y requiere revisión humana.','drift_status':'KS necesita una cohorte, no se aplica a una sola cuenta.'})
    except (ImportError,OSError,ValueError,KeyError) as exc:
        result['fallback_reason']=f'Modelo no disponible o incompatible: {type(exc).__name__}'
    return result

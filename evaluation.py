"""Honest classification evaluation and paired statistical comparisons.

Fold confidence intervals describe fold dispersion, not independent population samples.
"""
from __future__ import annotations
import numpy as np


def classification_metrics(y_true, y_pred, probabilities=None, classes=None):
    from sklearn import metrics as m
    y, pred = np.asarray(y_true), np.asarray(y_pred)
    labels = list(classes if classes is not None else np.unique(y))
    result = {"accuracy": float(m.accuracy_score(y, pred)),
              "precision": float(m.precision_score(y, pred, average="weighted", zero_division=0)),
              "recall": float(m.recall_score(y, pred, average="weighted", zero_division=0)),
              "f1": float(m.f1_score(y, pred, average="weighted", zero_division=0)),
              "f1_macro": float(m.f1_score(y, pred, average="macro", labels=labels, zero_division=0)),
              "mcc": float(m.matthews_corrcoef(y, pred))}
    cm = m.confusion_matrix(y, pred, labels=labels)
    result.update(classes=labels, confusion_matrix=cm.tolist(),
                  confusion_normalized=np.divide(cm, cm.sum(axis=1, keepdims=True), out=np.zeros_like(cm, dtype=float), where=cm.sum(axis=1, keepdims=True)!=0).tolist())
    # Missing positives/negatives are undefined, never fabricated zeros.
    result.update(roc_auc=None, pr_auc=None, curves={})
    if probabilities is not None:
        p = np.asarray(probabilities)
        aucs, aps = [], []
        for i, label in enumerate(labels):
            binary = (y == label).astype(int)
            if len(np.unique(binary)) < 2:
                result['curves'][label] = {"reason": "Clase sin positivos o negativos en esta partición"}
                continue
            fpr, tpr, thresholds = m.roc_curve(binary, p[:, i])
            precision, recall, pr_thresholds = m.precision_recall_curve(binary, p[:, i])
            aucs.append(float(m.roc_auc_score(binary, p[:, i])))
            aps.append(float(m.average_precision_score(binary, p[:, i])))
            result['curves'][label] = {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "roc_thresholds": [float(v) if np.isfinite(v) else None for v in thresholds], "precision": precision.tolist(), "recall": recall.tolist(), "pr_thresholds": pr_thresholds.tolist(), "roc_auc": aucs[-1], "pr_auc": aps[-1]}
        if len(aucs) == len(labels):
            result.update(roc_auc=float(np.mean(aucs)), pr_auc=float(np.mean(aps)))
    critical = labels.index('Crítico') if 'Crítico' in labels else None
    errors = int((y != pred).sum())
    critical_fn = int(cm[critical].sum() - cm[critical, critical]) if critical is not None else 0
    result.update(asymmetric_cost=errors + 4 * critical_fn,
                  cost_definition="Error ordinario = 1; falso negativo crítico = 5 (coste analítico, no calibrado).",
                  interpretation=f"F1 macro {result['f1_macro']:.3f}; {errors} errores, {critical_fn} falsos negativos críticos; etiquetas derivadas de reglas, no verdad clínica independiente.")
    return result


def aggregate_folds(folds):
    if not folds:
        raise ValueError('Se requieren resultados de folds reales')
    result = {}
    for key in ('accuracy', 'precision', 'recall', 'f1', 'f1_macro', 'mcc', 'roc_auc', 'pr_auc'):
        values = [float(f[key]) for f in folds if f.get(key) is not None]
        result[key] = {"mean": float(np.mean(values)), "std": float(np.std(values, ddof=1)) if len(values)>1 else None, "variance": float(np.var(values, ddof=1)) if len(values)>1 else None, "n": len(values)} if values else {"mean": None, "std": None, "variance": None, "n": 0}
    return result


def bootstrap_interval(y_true, y_pred, n_resamples=1000, seed=42):
    from sklearn.metrics import f1_score
    y, p = np.asarray(y_true), np.asarray(y_pred)
    if len(y) < 2 or len(y) != len(p) or n_resamples < 2:
        raise ValueError('Bootstrap requiere >=2 observaciones y remuestreos')
    rng, labels = np.random.default_rng(seed), np.unique(y)
    values = []
    for _ in range(n_resamples):
        idx = rng.integers(0, len(y), len(y))
        values.append(f1_score(y[idx], p[idx], labels=labels, average='macro', zero_division=0))
    lo, hi = np.quantile(values, [0.025, 0.975])
    return {"metric": "f1_macro", "low": float(lo), "high": float(hi), "resamples": n_resamples, "method": "paired percentile bootstrap, test predictions fixed"}


def compare_models(scores):
    """Caller must supply same fold IDs/order and dataset for every model."""
    from scipy.stats import wilcoxon, friedmanchisquare, rankdata, studentized_range
    names, values = list(scores), np.asarray(list(scores.values()), dtype=float)
    if len(names)<2 or values.ndim != 2 or values.shape[1]<3 or not np.isfinite(values).all():
        raise ValueError('Requiere >=2 modelos y >=3 folds emparejados finitos')
    if len(names)==2:
        p = 1.0 if np.array_equal(values[0], values[1]) else float(wilcoxon(*values).pvalue)
        return {"test": "Wilcoxon", "p_value": p, "warning": "Pocos folds: baja potencia; folds de CV no son independientes."}
    ranks = np.array([rankdata(-values[:, i]) for i in range(values.shape[1])]).mean(axis=0)
    k, n = values.shape
    same = all(np.array_equal(values[0], row) for row in values[1:])
    p = 1.0 if same else float(friedmanchisquare(*values).pvalue)
    pairs = []
    for i in range(k):
        for j in range(i+1,k):
            q = abs(ranks[i]-ranks[j])/np.sqrt(k*(k+1)/(6*n))
            pairs.append({"models": [names[i],names[j]], "p_value": float(studentized_range.sf(q*np.sqrt(2), k, np.inf))})
    return {"test": "Friedman + Nemenyi", "p_value": p, "mean_ranks": dict(zip(names,ranks.tolist())), "posthoc": pairs, "warning": "Exploratorio: folds de CV dependientes; pocos folds limitan potencia."}


def drift_test(reference, observed):
    from scipy.stats import ks_2samp
    a, b = np.asarray(reference,dtype=float), np.asarray(observed,dtype=float)
    if len(a)<2 or len(b)<2 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('KS requiere dos muestras finitas de >=2; una cuenta no constituye una muestra de drift')
    result = ks_2samp(a,b)
    return {"statistic": float(result.statistic), "p_value": float(result.pvalue), "drift": bool(result.pvalue<0.05), "warning": "KS no ajustado por comparaciones múltiples"}

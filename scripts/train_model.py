"""Train against an explicit CSV and persist job/results; never seeds the application DB."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',required=True)
    parser.add_argument('--database-url',required=True,help='Explicit job database URL, SQLite or PostgreSQL')
    parser.add_argument('--model',default='logistic',choices=['logistic','random_forest','gradient_boosting','mlp'])
    parser.add_argument('--outer-folds',type=int,default=5)
    parser.add_argument('--inner-folds',type=int,default=3)
    parser.add_argument('--trials',type=int,default=50)
    parser.add_argument('--stratify',choices=['joint','severity'],default='joint')
    parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args()
    import pandas as pd
    from sqlalchemy import create_engine
    from optuna_service import run_training_sync
    rows=pd.read_csv(args.csv).astype(object).where(pd.notna(pd.read_csv(args.csv)),None).to_dict('records')
    job=run_training_sync(rows,dict(model=args.model,outer_folds=args.outer_folds,inner_folds=args.inner_folds,n_trials=args.trials,stratify=args.stratify,seed=args.seed),actor='cli',engine=create_engine(args.database_url))
    print(json.dumps(job,ensure_ascii=False,indent=2))
    return 0 if job['status']=='completed' else 1


if __name__=='__main__':
    raise SystemExit(main())

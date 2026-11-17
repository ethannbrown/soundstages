import sys
import time

import pandas as pd

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, PREDICTIONS, RESULTS
from folds import AUDIO, design, fit_linear, frame, split

# The context regressions from baselines.py plus the ten audio features
start = time.perf_counter()
df = pd.read_parquet(MODEL_TABLE)
y = df['popularity'].to_numpy()
artists = df['uuid'].cat.codes.to_numpy()
print(f'Loaded {len(df):,} tracks')

out = []
coefs = []
setups = {
    'between': (['log_listeners', 'log_duration'] + AUDIO, ['genre', 'era']),
    'within': (['log_duration'] + AUDIO, ['era']),
}
for setup, (numeric, categorical) in setups.items():
    X, names = design(df, numeric, categorical)
    groups = artists if setup == 'within' else None
    for fold, train, test in split(df, setup):
        y_test, y_pred, coef = fit_linear(X, y, len(numeric), train, test, groups=groups)
        out.append(frame(df, test, 'linear', setup, True, fold, y_test, y_pred))

        # Audio coefficients, per sd of each feature
        coef = dict(zip(names, coef, strict=True))
        coefs += [{'setup': setup, 'fold': fold, 'feature': col, 'coef': coef[col]} for col in AUDIO]
    print(f'Fit the {setup}-artist regression with audio')

PREDICTIONS.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)
out = pd.concat(out, ignore_index=True)
out.to_parquet(PREDICTIONS / 'linear.parquet')
print(f'Saved {len(out):,} predictions to linear.parquet')

coefs = pd.DataFrame(coefs)
coefs.to_csv(RESULTS / 'coefficients.csv', index=False)
mean = coefs.groupby(['setup', 'feature'])['coef'].mean()
for setup in setups:
    top = mean[setup].abs().idxmax()
    print(f'Largest {setup}-artist audio coefficient is {top}, {mean[setup][top]:.2f} points per sd')
print(f'Ran in {time.perf_counter() - start:.0f} s')

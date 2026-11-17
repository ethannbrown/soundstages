import sys
import time

import numpy as np
import pandas as pd
from statsmodels.regression.quantile_regression import QuantReg

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, RESULTS, SEED
from folds import AUDIO, design, split, standardize

QUANTILES = [0.25, 0.5, 0.75, 0.9, 0.99]


def fit_quantile(X, y, n_numeric, q, train, test):
    """One fold of quantile regression. Returns test predictions and coefficients without the constant."""
    X_train, X_test = standardize(X[train], X[test], n_numeric)
    X_train = np.column_stack([np.ones(len(X_train)), X_train])
    X_test = np.column_stack([np.ones(len(X_test)), X_test])
    params = QuantReg(y[train], X_train).fit(q=q).params
    return X_test @ params, params[1:]


def pinball(y, pred, q) -> float:
    diff = y - pred
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))


# Heard tracks only, sampled to keep the fits manageable
df = pd.read_parquet(MODEL_TABLE)
heard = df[df['heard']]
df = heard.sample(250_000, random_state=SEED).reset_index(drop=True)
print(f'Sampled {len(df):,} of {len(heard):,} heard tracks')

# Year as categories, everything before 1960 in one
year = df['year'].astype(int)
df['year_cat'] = year.astype(str).where(year >= 1960, '<1960').astype('category')
y = df['popularity'].to_numpy()

context = ['log_listeners', 'log_duration']
X_context, _ = design(df, context, ['genre', 'year_cat'])
X_audio, names = design(df, context + AUDIO, ['genre', 'year_cat'])
n_audio = len(context + AUDIO)
print(f'Built designs with {X_context.shape[1]} context and {X_audio.shape[1]} audio columns')

# Time one fit before committing to all 50
if '--all' not in sys.argv:
    _, train, test = next(split(df, 'between'))
    times = []
    for q in [0.5, 0.99]:
        start = time.perf_counter()
        fit_quantile(X_audio, y, n_audio, q, train, test)
        times.append(time.perf_counter() - start)
        print(f'One fit at q={q} took {times[-1]:.0f} s')
    print(f'All 50 fits would take about {max(times) * 50 / 60:.0f} min. Rerun with --all to fit them')
    sys.exit()

scores = []
coefs = []
for q in QUANTILES:
    for fold, train, test in split(df, 'between'):
        # Intercept only, the baseline for r1
        null = QuantReg(y[train], np.ones(len(train))).fit(q=q).params[0]
        loss_null = pinball(y[test], np.full(len(test), null), q)

        pred, _ = fit_quantile(X_context, y, len(context), q, train, test)
        loss = pinball(y[test], pred, q)
        scores.append({'quantile': q, 'fold': fold, 'audio': False, 'pinball': loss, 'r1': 1 - loss / loss_null})

        pred, coef = fit_quantile(X_audio, y, n_audio, q, train, test)
        loss = pinball(y[test], pred, q)
        scores.append({'quantile': q, 'fold': fold, 'audio': True, 'pinball': loss, 'r1': 1 - loss / loss_null})

        # Audio coefficients, per sd of each feature
        coef = dict(zip(names, coef, strict=True))
        coefs += [{'quantile': q, 'fold': fold, 'feature': col, 'coef': coef[col]} for col in AUDIO]
    print(f'Fit the q={q} regressions')

RESULTS.mkdir(exist_ok=True)
scores = pd.DataFrame(scores)
scores.to_csv(RESULTS / 'quantile_scores.csv', index=False)
coefs = pd.DataFrame(coefs)
coefs.to_csv(RESULTS / 'quantile_coefs.csv', index=False)
print(f'Saved {len(scores)} scores and {len(coefs)} coefficients')

# Percent reduction in pinball loss per fold, then audio coefficients
wide = scores.pivot_table(index=['quantile', 'fold'], columns='audio', values='pinball')
gain = 100 * (1 - wide[True] / wide[False])
for q in QUANTILES:
    print(f'At q={q}, audio cut pinball loss by {gain[q].mean():.1f}% (sd {gain[q].std():.1f}%) across folds')
    r1 = scores[scores['quantile'] == q].groupby('audio')['r1'].agg(['mean', 'std'])
    print(
        f'Background-only r1 is {r1.loc[False, "mean"]:.3f} (sd {r1.loc[False, "std"]:.3f}), '
        f'with audio {r1.loc[True, "mean"]:.3f} (sd {r1.loc[True, "std"]:.3f})'
    )
    stats = coefs[coefs['quantile'] == q].groupby('feature')['coef'].agg(['mean', 'std'])
    for col in AUDIO:
        print(f'{col} {stats.loc[col, "mean"]:.2f} points per sd (sd {stats.loc[col, "std"]:.2f})')

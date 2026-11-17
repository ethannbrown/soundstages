import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb
from statsmodels.regression.quantile_regression import QuantReg

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, N_FOLDS, RESULTS, SEED
from folds import AUDIO, CONTEXT, pinball, split

BACKGROUND = CONTEXT + ['year', 'genre']
FEATURES = BACKGROUND + AUDIO

# Three quantiles, up to 100,000 tracks per subset
QUANTILES = [0.25, 0.5, 0.9]
SIZE = 100_000

df = pd.read_parquet(MODEL_TABLE)
heard = df[df['heard']]
subsets = ['all', 'Acoustic', 'Electric', 'Loudness war', 'Streaming']


def subset_sample(subset):
    """Heard tracks in one subset, up to SIZE of them."""
    rows = heard if subset == 'all' else heard[heard['sonic_era'] == subset]
    sub = rows.sample(min(len(rows), SIZE), random_state=SEED).reset_index(drop=True)
    sub['year'] = sub['year'].astype(float)
    sub['genre'] = sub['genre'].cat.remove_unused_categories()
    return sub, len(rows)


def fit_boost(X, y, q, train, test):
    """One fold of XGBoost quantile regression; early stops on a random 10% of training rows"""
    rng = np.random.default_rng(SEED)
    stop = rng.random(len(train)) < 0.1
    fit, val = train[~stop], train[stop]
    model = xgb.XGBRegressor(
        objective='reg:quantileerror',
        quantile_alpha=q,
        max_depth=6,
        learning_rate=0.1,
        n_estimators=1000,
        early_stopping_rounds=50,
        tree_method='hist',
        enable_categorical=True,
        n_jobs=-1,
        random_state=SEED,
    )
    model.fit(X.iloc[fit], y[fit], eval_set=[(X.iloc[val], y[val])], verbose=False)
    return model.predict(X.iloc[test]), model


def shap_summary(model, X_test):
    """Mean absolute SHAP per feature; mean SHAP above vs at or below its median"""
    dtest = xgb.DMatrix(X_test, enable_categorical=True)
    trees = (0, model.best_iteration + 1)
    contribs = model.get_booster().predict(dtest, pred_contribs=True, iteration_range=trees)
    contribs = contribs[:, :-1]  # Last column is the bias
    rows = []
    for j, col in enumerate(X_test.columns):
        shap = contribs[:, j]
        high = low = np.nan
        if col == 'mode':
            # Major vs minor
            x = X_test[col].to_numpy()
            high, low = shap[x == 1].mean(), shap[x == 0].mean()
        elif col != 'genre':
            x = X_test[col].to_numpy()
            above = x > np.median(x)
            high, low = shap[above].mean(), shap[~above].mean()
        rows.append({'feature': col, 'mean_abs': np.abs(shap).mean(), 'mean_high': high, 'mean_low': low})
    return rows


# Time one audio fit before committing to all of them
if '--all' not in sys.argv:
    sub, n = subset_sample('all')
    print(f'Sampled {len(sub):,} of {n:,} heard tracks')
    y = sub['popularity'].to_numpy()
    _, train, test = next(split(sub, 'between'))
    times = []
    for q in [0.5, 0.9]:
        start = time.perf_counter()
        _, model = fit_boost(sub[FEATURES], y, q, train, test)
        shap_summary(model, sub[FEATURES].iloc[test])
        times.append(time.perf_counter() - start)
        print(f'One audio fit at q={q} took {times[-1]:.0f} s and stopped at {model.best_iteration + 1} trees')
    n_fits = len(subsets) * len(QUANTILES) * N_FOLDS * 2
    print(f'All {n_fits} fits would take about {max(times) * n_fits / 60:.0f} min. Rerun with --all to fit them')
    sys.exit()

scores = []
shaps = []
for subset in subsets:
    sub, n = subset_sample(subset)
    y = sub['popularity'].to_numpy()
    for q in QUANTILES:
        for fold, train, test in split(sub, 'between'):
            # Intercept only, the baseline for r1
            null = QuantReg(y[train], np.ones(len(train))).fit(q=q).params[0]
            loss_null = pinball(y[test], np.full(len(test), null), q)
            key = {'subset': subset, 'quantile': q, 'fold': fold}
            scores.append({**key, 'model': 'intercept', 'pinball': loss_null, 'r1': 0.0})

            for name, cols in [('background', BACKGROUND), ('audio', FEATURES)]:
                pred, model = fit_boost(sub[cols], y, q, train, test)
                loss = pinball(y[test], pred, q)
                scores.append({**key, 'model': name, 'pinball': loss, 'r1': 1 - loss / loss_null})

            # SHAP from the audio model
            shaps += [{**key, **row} for row in shap_summary(model, sub[FEATURES].iloc[test])]
        print(f'Fit the {subset} subset at q={q} on {len(sub):,} of {n:,} heard tracks')

scores = pd.DataFrame(scores)
shaps = pd.DataFrame(shaps)

RESULTS.mkdir(exist_ok=True)
scores.to_csv(RESULTS / 'boost_scores.csv', index=False)
shaps.to_csv(RESULTS / 'boost_shap.csv', index=False)
print(f'Saved {len(scores)} scores and {len(shaps)} SHAP rows')

# r1 per fold, and the gain from audio
wide = scores.pivot_table(index=['subset', 'quantile', 'fold'], columns='model', values='r1')
wide['gain'] = wide['audio'] - wide['background']
stats = wide.groupby(['subset', 'quantile']).agg(['mean', 'std'])
for subset in subsets:
    for q in QUANTILES:
        s = stats.loc[(subset, q)]
        print(
            f'In the {subset} subset at q={q}, background r1 is {s["background", "mean"]:.3f} '
            f'(sd {s["background", "std"]:.3f}), with audio {s["audio", "mean"]:.3f} '
            f'(sd {s["audio", "std"]:.3f}), a gain of {s["gain", "mean"]:.3f} (sd {s["gain", "std"]:.3f})'
        )

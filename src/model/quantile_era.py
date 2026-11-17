import sys
import time

import pandas as pd

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, RESULTS, SEED
from folds import AUDIO, CONTEXT, QUANTILES, fit_quantile, quantile_designs, quantile_folds, split

df = pd.read_parquet(MODEL_TABLE)
heard = df[df['heard']]
eras = list(heard['sonic_era'].cat.categories)


def era_sample(era):
    """Heard tracks in one era, up to 250,000 of them."""
    rows = heard[heard['sonic_era'] == era]
    return rows.sample(min(len(rows), 250_000), random_state=SEED).reset_index(drop=True), len(rows)


# Time one audio fit per era before committing to all of them
if '--all' not in sys.argv:
    total = 0
    for era in eras:
        sub, n = era_sample(era)
        _, X_audio, _ = quantile_designs(sub)
        y = sub['popularity'].to_numpy()
        _, train, test = next(split(sub, 'between'))
        times = []
        for q in [0.5, 0.99]:
            start = time.perf_counter()
            fit_quantile(X_audio, y, len(CONTEXT + AUDIO), q, train, test)
            times.append(time.perf_counter() - start)
        total += max(times) * 50
        print(f'The {era} era ({len(sub):,} tracks) would take about {max(times) * 50 / 60:.0f} min')
    print(f'All four eras would take about {total / 60:.0f} min. Rerun with --all to fit them')
    sys.exit()

scores = []
coefs = []
for era in eras:
    sub, n = era_sample(era)
    s, c = quantile_folds(sub)
    scores.append(s.assign(era=era))
    coefs.append(c.assign(era=era))
    print(f'Fit the {era} era on {len(sub):,} of {n:,} heard tracks')

scores = pd.concat(scores, ignore_index=True)
scores = scores[['era', 'quantile', 'fold', 'model', 'pinball', 'r1']]
coefs = pd.concat(coefs, ignore_index=True)
coefs = coefs[['era', 'quantile', 'fold', 'feature', 'coef']]

RESULTS.mkdir(exist_ok=True)
scores.to_csv(RESULTS / 'quantile_era_scores.csv', index=False)
coefs.to_csv(RESULTS / 'quantile_era_coefs.csv', index=False)
print(f'Saved {len(scores)} scores and {len(coefs)} coefficients')

# r1 per fold, and the gain from audio
wide = scores.pivot_table(index=['era', 'quantile', 'fold'], columns='model', values='r1')
wide['gain'] = wide['audio'] - wide['background']
stats = wide.groupby(['era', 'quantile']).agg(['mean', 'std'])
for era in eras:
    for q in QUANTILES:
        s = stats.loc[(era, q)]
        print(
            f'In the {era} era at q={q}, background r1 is {s["background", "mean"]:.3f} '
            f'(sd {s["background", "std"]:.3f}), with audio {s["audio", "mean"]:.3f} '
            f'(sd {s["audio", "std"]:.3f}), a gain of {s["gain", "mean"]:.3f} (sd {s["gain", "std"]:.3f})'
        )

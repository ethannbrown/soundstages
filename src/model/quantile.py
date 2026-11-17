import sys
import time

import pandas as pd

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, RESULTS, SEED
from folds import AUDIO, CONTEXT, QUANTILES, fit_quantile, quantile_designs, quantile_folds, split

# Heard tracks only, sampled to keep the fits manageable
df = pd.read_parquet(MODEL_TABLE)
heard = df[df['heard']]
df = heard.sample(250_000, random_state=SEED).reset_index(drop=True)
print(f'Sampled {len(df):,} of {len(heard):,} heard tracks')

# Time one fit before committing to all 50
if '--all' not in sys.argv:
    X_context, X_audio, _ = quantile_designs(df)
    print(f'Built designs with {X_context.shape[1]} context and {X_audio.shape[1]} audio columns')
    y = df['popularity'].to_numpy()
    _, train, test = next(split(df, 'between'))
    times = []
    for q in [0.5, 0.99]:
        start = time.perf_counter()
        fit_quantile(X_audio, y, len(CONTEXT + AUDIO), q, train, test)
        times.append(time.perf_counter() - start)
        print(f'One fit at q={q} took {times[-1]:.0f} s')
    print(f'All 50 fits would take about {max(times) * 50 / 60:.0f} min. Rerun with --all to fit them')
    sys.exit()

scores, coefs = quantile_folds(df)

# Background and audio rows only, audio as a flag
scores = scores[scores['model'] != 'intercept'].reset_index(drop=True)
scores.insert(2, 'audio', scores.pop('model') == 'audio')

RESULTS.mkdir(exist_ok=True)
scores.to_csv(RESULTS / 'quantile_scores.csv', index=False)
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

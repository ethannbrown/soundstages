import sys

import numpy as np
import pandas as pd

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, PREDICTIONS, RESULTS
from folds import mse, r2, rmse

table = pd.read_parquet(MODEL_TABLE, columns=['trackID', 'uuid', 'band', 'genre'])
KEYS = ['model', 'setup', 'audio']

# Expected popularity: the context-only between-artist regression, one value per track
expected = pd.read_parquet(
    PREDICTIONS / 'baselines.parquet',
    columns=['trackID', 'y_pred'],
    filters=[('model', '==', 'linear'), ('setup', '==', 'between'), ('audio', '==', False)],
)
expected = expected.rename(columns={'y_pred': 'expected'})
assert expected['trackID'].is_unique, 'expected popularity has more than one value per track'
expected = expected.merge(table[['trackID', 'uuid']], on='trackID')

NAMES = ['Unheard', 'Obscure', 'Niche', 'Established', 'Popular', 'Hit']
tier = pd.cut(expected['expected'], [-np.inf, 1, 10, 30, 50, 70, np.inf], right=False, labels=NAMES)
expected['tier'] = tier.astype(str)


def size(tier: list[str]) -> tuple[int, int]:
    """Tracks and artists in a tier, given the original tier names it holds."""
    rows = expected['tier'].isin(tier)
    return int(rows.sum()), expected.loc[rows, 'uuid'].nunique()


def label(tier: list[str]) -> str:
    """Niche+ when a merged tier reaches the top, Niche-Established when it stops short."""
    if len(tier) == 1:
        return tier[0]
    if tier[-1] == NAMES[-1]:
        return f'{tier[0]}+'
    return f'{tier[0]}-{tier[-1]}'


# Fold the highest small tier into the one below until every tier has
# 20,000+ tracks and 500+ artists
tiers = [[name] for name in NAMES]
while True:
    small = [i for i, tier in enumerate(tiers) if size(tier)[0] < 20_000 or size(tier)[1] < 500]
    if not small:
        break
    i = small[-1]
    assert i > 0, f'{label(tiers[0])} is too small and has no tier below it'
    tracks, artists = size(tiers[i])
    print(f'Merged {label(tiers[i])} into {label(tiers[i - 1])} ({tracks:,} tracks, {artists:,} artists)')
    tiers[i - 1] += tiers.pop(i)

for tier in tiers:
    tracks, artists = size(tier)
    print(f'{label(tier)} has {tracks:,} tracks from {artists:,} artists')
ORDER = [label(tier) for tier in tiers]
expected['tier'] = expected['tier'].map({name: label(tier) for tier in tiers for name in tier})

# Curve: 20 equal-count groups of expected popularity
expected['curve'] = pd.qcut(expected['expected'], 20, labels=False)
ranges = expected.groupby('curve')['expected'].agg(expected_min='min', expected_max='max')

# Same tier and curve group for a track in both setups
table = table.drop(columns='uuid').merge(expected[['trackID', 'tier', 'curve']], on='trackID')

scores = []
errors = []
for path in sorted(PREDICTIONS.glob('*.parquet')):
    preds = pd.read_parquet(path)
    assert preds['y_pred'].notna().all(), f'{path.name} has missing predictions'

    # One model, setup and audio choice at a time
    for key, group in preds.groupby(KEYS):
        group = group.merge(table, on='trackID', how='left')
        name = dict(zip(KEYS, key, strict=True))

        per_fold = [
            {'r2': r2(fold['y_true'], fold['y_pred']), 'rmse': rmse(fold['y_true'], fold['y_pred'])}
            for _, fold in group.groupby('fold')
        ]
        per_fold = pd.DataFrame(per_fold)
        scores.append(
            name
            | {
                'r2': r2(group['y_true'], group['y_pred']),
                'rmse': rmse(group['y_true'], group['y_pred']),
                'r2_fold_mean': per_fold['r2'].mean(),
                'r2_fold_sd': per_fold['r2'].std(),
                'rmse_fold_mean': per_fold['rmse'].mean(),
                'rmse_fold_sd': per_fold['rmse'].std(),
            }
        )

        # MSE overall and per tier, curve group, genre and band, pooled (fold -1) and per fold
        for level in ['overall', 'tier', 'curve', 'genre', 'band']:
            by = [] if level == 'overall' else [level]
            for fold in [-1, *range(group['fold'].max() + 1)]:
                rows = group if fold == -1 else group[group['fold'] == fold]
                cells = rows.groupby(by, observed=True) if by else [('all', rows)]
                for cell, part in cells:
                    cell = cell[0] if isinstance(cell, tuple) else cell
                    error = mse(part['y_true'], part['y_pred'])
                    errors.append(
                        name | {'level': level, 'group': str(cell), 'fold': fold, 'tracks': len(part), 'mse': error}
                    )
    print(f'Scored {path.name}')

RESULTS.mkdir(exist_ok=True)
scores = pd.DataFrame(scores)
scores.to_csv(RESULTS / 'scores.csv', index=False)

# Audio's added value: MSE without audio minus MSE with it, same model and setup,
# and that gain as a percent of the MSE without audio
errors = pd.DataFrame(errors)
cell = ['model', 'setup', 'level', 'group']
mse_table = errors.pivot_table(index=cell + ['fold'], columns='audio', values='mse')
mse_table = mse_table.dropna()  # Models fit only one way have nothing to compare
mse_table['gain'] = mse_table[False] - mse_table[True]
mse_table['pct'] = mse_table['gain'] / mse_table[False] * 100

gain = mse_table['gain'].unstack('fold')
pct = mse_table['pct'].unstack('fold')
folds = [fold for fold in gain.columns if fold != -1]
tracks = errors[errors['fold'] == -1].groupby(cell)['tracks'].first()
gain = pd.DataFrame(
    {
        'tracks': tracks.reindex(gain.index),
        'gain': gain[-1],
        'fold_mean': gain[folds].mean(axis=1),
        'fold_sd': gain[folds].std(axis=1),
        'pct': pct[-1],
        'pct_fold_mean': pct[folds].mean(axis=1),
        'pct_fold_sd': pct[folds].std(axis=1),
    }
).reset_index()

# Headline: overall, by expected-popularity tier, by genre
headline = gain[gain['level'].isin(['overall', 'tier', 'genre'])]
headline.to_csv(RESULTS / 'audio_gain.csv', index=False)

curve = gain[gain['level'] == 'curve'].drop(columns='level')
curve['group'] = curve['group'].astype(int)
curve = curve.merge(ranges, left_on='group', right_index=True).sort_values(['model', 'setup', 'group'])
curve.to_csv(RESULTS / 'audio_gain_curve.csv', index=False)

# Grouped by actual popularity, which conditions on the outcome. Descriptive only.
bands = gain[gain['level'] == 'band'].drop(columns='level')
bands.to_csv(RESULTS / 'descriptive_gain_by_actual_band.csv', index=False)

for row in scores.itertuples():
    with_audio = 'with audio' if row.audio else 'without audio'
    print(f'{row.model} {row.setup} {with_audio}: R2 {row.r2:.3f} (fold sd {row.r2_fold_sd:.3f}), RMSE {row.rmse:.2f}')

for row in gain[gain['level'] == 'overall'].itertuples():
    print(f'Audio lowered {row.setup}-artist {row.model} MSE by {row.gain:.2f} (fold sd {row.fold_sd:.2f})')

by_tier = gain[gain['level'] == 'tier'].set_index(['model', 'setup', 'group'])
for model, setup in gain.loc[gain['level'] == 'overall', ['model', 'setup']].itertuples(index=False):
    parts = ', '.join(
        f'{tier} {by_tier.loc[(model, setup, tier), "fold_mean"]:.2f} '
        f'(sd {by_tier.loc[(model, setup, tier), "fold_sd"]:.2f})'
        for tier in ORDER
    )
    print(f'{setup.capitalize()}-artist {model} gain by tier: {parts}')

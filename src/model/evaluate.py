import sys

import pandas as pd

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, PREDICTIONS, RESULTS
from folds import mse, r2, rmse

table = pd.read_parquet(MODEL_TABLE, columns=['trackID', 'genre'])
KEYS = ['model', 'setup', 'audio']

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

        # MSE overall and per genre, pooled (fold -1) and per fold
        for level in ['overall', 'genre']:
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

# Audio gain (MSE without audio minus with), also as a percent
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

gain.to_csv(RESULTS / 'audio_gain.csv', index=False)

for row in scores.itertuples():
    with_audio = 'with audio' if row.audio else 'without audio'
    print(f'{row.model} {row.setup} {with_audio}: R2 {row.r2:.3f} (fold sd {row.r2_fold_sd:.3f}), RMSE {row.rmse:.2f}')

for row in gain[gain['level'] == 'overall'].itertuples():
    print(f'Audio lowered {row.setup}-artist {row.model} MSE by {row.gain:.2f} (fold sd {row.fold_sd:.2f})')

import sys
import time

import pandas as pd

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, PREDICTIONS, RESULTS
from folds import mse, r2, rmse

start = time.perf_counter()
table = pd.read_parquet(MODEL_TABLE, columns=['trackID', 'band', 'genre'])
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

        # MSE overall, by band and by genre, pooled (fold -1) and per fold
        for level in ['overall', 'band', 'genre']:
            by = [] if level == 'overall' else [level]
            for fold in [-1, *range(group['fold'].max() + 1)]:
                rows = group if fold == -1 else group[group['fold'] == fold]
                cells = rows.groupby(by, observed=True) if by else [('all', rows)]
                for cell, part in cells:
                    cell = cell[0] if isinstance(cell, tuple) else cell
                    error = mse(part['y_true'], part['y_pred'])
                    errors.append(name | {'level': level, 'group': str(cell), 'fold': fold, 'mse': error})
    print(f'Scored {path.name}')

RESULTS.mkdir(exist_ok=True)
scores = pd.DataFrame(scores)
scores.to_csv(RESULTS / 'scores.csv', index=False)

# Audio's added value: MSE without audio minus MSE with it, same model and setup
errors = pd.DataFrame(errors)
mse_table = errors.pivot_table(index=['model', 'setup', 'level', 'group', 'fold'], columns='audio', values='mse')
mse_table = mse_table.dropna()  # Models fit only one way have nothing to compare
mse_table['gain'] = mse_table[False] - mse_table[True]
gain = mse_table['gain'].unstack('fold')
gain = pd.DataFrame(
    {
        'gain': gain[-1],
        'fold_mean': gain.drop(columns=-1).mean(axis=1),
        'fold_sd': gain.drop(columns=-1).std(axis=1),
    }
).reset_index()
gain.to_csv(RESULTS / 'audio_gain.csv', index=False)

for row in scores.itertuples():
    with_audio = 'with audio' if row.audio else 'without audio'
    print(f'{row.model} {row.setup} {with_audio}: R2 {row.r2:.3f} (fold sd {row.r2_fold_sd:.3f}), RMSE {row.rmse:.2f}')

for row in gain[gain['level'] == 'overall'].itertuples():
    print(f'Audio lowered {row.setup}-artist {row.model} MSE by {row.gain:.2f} (fold sd {row.fold_sd:.2f})')

order = ['Zero', 'Low', 'Mid', 'High', 'Top']
bands = gain[gain['level'] == 'band'].set_index(['model', 'setup', 'group'])['gain']
for model, setup in gain.loc[gain['level'] == 'overall', ['model', 'setup']].itertuples(index=False):
    parts = ', '.join(f'{band} {bands[(model, setup, band)]:.2f}' for band in order)
    print(f'{setup.capitalize()}-artist {model} gain by band: {parts}')
print(f'Ran in {time.perf_counter() - start:.0f} s')

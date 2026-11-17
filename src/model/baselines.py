import sys

import numpy as np
import pandas as pd

sys.path.append('.')  # Run from project root
from config import MODEL_TABLE, PREDICTIONS
from folds import design, fit_linear, frame, split

df = pd.read_parquet(MODEL_TABLE)
y = df['popularity'].to_numpy()
genres = df['genre'].cat.codes.to_numpy()
artists = df['uuid'].cat.codes.to_numpy()
print(f'Loaded {len(df):,} tracks')

out = []

# Between artists
numeric = ['log_listeners', 'log_duration']
X, _ = design(df, numeric, ['genre', 'era'])
for fold, train, test in split(df, 'between'):
    out.append(frame(df, test, 'global_mean', 'between', False, fold, y[test], np.full(len(test), y[train].mean())))

    genre_mean = np.bincount(genres[train], weights=y[train]) / np.bincount(genres[train])
    out.append(frame(df, test, 'genre_mean', 'between', False, fold, y[test], genre_mean[genres[test]]))

    y_test, y_pred, _ = fit_linear(X, y, len(numeric), train, test)
    out.append(frame(df, test, 'linear', 'between', False, fold, y_test, y_pred))
print('Fit the between-artist baselines')

# Within artists
numeric = ['log_duration']
X, _ = design(df, numeric, ['era'])
for fold, train, test in split(df, 'within'):
    y_test, y_pred, _ = fit_linear(X, y, len(numeric), train, test, groups=artists)
    out.append(frame(df, test, 'zero', 'within', False, fold, y_test, np.zeros(len(test))))
    out.append(frame(df, test, 'linear', 'within', False, fold, y_test, y_pred))
print('Fit the within-artist baselines')

PREDICTIONS.mkdir(exist_ok=True)
out = pd.concat(out, ignore_index=True)
out.to_parquet(PREDICTIONS / 'baselines.parquet')
print(f'Saved {len(out):,} predictions to baselines.parquet')

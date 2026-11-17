import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.regression.quantile_regression import QuantReg

from config import N_FOLDS

QUANTILES = [0.25, 0.5, 0.75, 0.9, 0.99]
CONTEXT = ['log_listeners', 'log_duration']

AUDIO = [
    'acousticness',
    'danceability',
    'energy',
    'instrumentalness',
    'liveness',
    'loudness',
    'mode',
    'speechiness',
    'tempo',
    'valence',
]


def assign_between(uuids: pd.Series, seed: int) -> pd.Series:
    """Shuffle the artists, then artist i goes to fold i % N_FOLDS."""
    uuids = uuids.astype(str)
    artists = np.random.default_rng(seed).permutation(np.sort(uuids.unique()))
    fold = dict(zip(artists, np.arange(len(artists)) % N_FOLDS, strict=True))
    return uuids.map(fold).astype('int8')


def assign_within(uuids: pd.Series, seed: int) -> pd.Series:
    """Shuffle each artist's tracks and randomly assigns them to the folds."""
    rng = np.random.default_rng(seed)
    rows = pd.DataFrame({'uuid': uuids.astype(str).to_numpy(), 'key': rng.random(len(uuids))}, index=uuids.index)
    artists = np.sort(rows['uuid'].unique())
    start = pd.Series(rng.integers(0, N_FOLDS, len(artists)), index=artists)

    rows = rows.sort_values(['uuid', 'key'])
    fold = (rows.groupby('uuid').cumcount() + rows['uuid'].map(start)) % N_FOLDS
    return fold.reindex(uuids.index).astype('int8')


def split(df: pd.DataFrame, setup: str):
    """Yields (fold, train, test) row positions; within uses in_within rows only"""
    if setup == 'between':
        rows = np.arange(len(df))
        fold = df['fold_between'].to_numpy()
    else:
        rows = np.flatnonzero(df['in_within'].to_numpy())
        fold = df['fold_within'].iloc[rows].astype(int).to_numpy()

    for k in range(N_FOLDS):
        yield k, rows[fold != k], rows[fold == k]


def demean(train: np.ndarray, test: np.ndarray, g_train: np.ndarray, g_test: np.ndarray):
    """Subtract each group's mean over the training rows from both train and test."""
    train = np.asarray(train, dtype=float)
    test = np.asarray(test, dtype=float)
    vector = train.ndim == 1
    if vector:
        train, test = train[:, None], test[:, None]

    size = max(g_train.max(), g_test.max()) + 1
    counts = np.bincount(g_train, minlength=size)

    # NaN mean for groups with no training rows
    with np.errstate(invalid='ignore'):
        means = np.column_stack(
            [np.bincount(g_train, weights=train[:, j], minlength=size) / counts for j in range(train.shape[1])]
        )
    train, test = train - means[g_train], test - means[g_test]

    if vector:
        return train[:, 0], test[:, 0]
    return train, test


def within_target(y: np.ndarray, groups: np.ndarray, train: np.ndarray, test: np.ndarray):
    """Popularity minus the artist's mean over training-fold rows only."""
    return demean(y[train], y[test], groups[train], groups[test])


def design(df: pd.DataFrame, numeric: list[str], categorical: list[str]):
    """Numeric columns and one-hot encoded variables"""
    dummies = pd.get_dummies(df[categorical], drop_first=True, dtype=float)
    X = np.column_stack([df[numeric].to_numpy(dtype=float), dummies.to_numpy()])
    return X, numeric + list(dummies.columns)


def standardize(train: np.ndarray, test: np.ndarray, n_numeric: int):
    """Scale the first n_numeric columns with the training rows' mean and sd."""
    train, test = train.copy(), test.copy()
    mean = train[:, :n_numeric].mean(axis=0)
    sd = train[:, :n_numeric].std(axis=0)
    train[:, :n_numeric] = (train[:, :n_numeric] - mean) / sd
    test[:, :n_numeric] = (test[:, :n_numeric] - mean) / sd
    return train, test


def fit_linear(X, y, n_numeric, train, test, groups=None):
    """One fold of linear regression; demeans by artist when groups is given"""
    X_train, X_test = standardize(X[train], X[test], n_numeric)
    y_train, y_test = y[train], y[test]
    if groups is not None:
        X_train, X_test = demean(X_train, X_test, groups[train], groups[test])
        y_train, y_test = within_target(y, groups, train, test)

    model = LinearRegression().fit(X_train, y_train)
    return y_test, model.predict(X_test), model.coef_


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


def quantile_designs(df: pd.DataFrame):
    """Context and audio designs, with year as categories (before 1960 in one) and unused categories dropped."""
    year = df['year'].astype(int)
    df = df.assign(
        year_cat=year.astype(str).where(year >= 1960, '<1960').astype('category'),
        genre=df['genre'].cat.remove_unused_categories(),
    )
    X_context, _ = design(df, CONTEXT, ['genre', 'year_cat'])
    X_audio, names = design(df, CONTEXT + AUDIO, ['genre', 'year_cat'])
    return X_context, X_audio, names


def quantile_folds(df: pd.DataFrame):
    """Intercept-only, background and audio quantile regressions on each between-artist fold"""
    X_context, X_audio, names = quantile_designs(df)
    y = df['popularity'].to_numpy()
    models = [('background', X_context, len(CONTEXT)), ('audio', X_audio, len(CONTEXT + AUDIO))]

    scores = []
    coefs = []
    for q in QUANTILES:
        for fold, train, test in split(df, 'between'):
            # Intercept only, the baseline for r1
            null = QuantReg(y[train], np.ones(len(train))).fit(q=q).params[0]
            loss_null = pinball(y[test], np.full(len(test), null), q)
            scores.append({'quantile': q, 'fold': fold, 'model': 'intercept', 'pinball': loss_null, 'r1': 0.0})

            for model, X, n_numeric in models:
                pred, coef = fit_quantile(X, y, n_numeric, q, train, test)
                loss = pinball(y[test], pred, q)
                r1 = 1 - loss / loss_null
                scores.append({'quantile': q, 'fold': fold, 'model': model, 'pinball': loss, 'r1': r1})

            # Audio coefficients from the last fit
            coef = dict(zip(names, coef, strict=True))
            coefs += [{'quantile': q, 'fold': fold, 'feature': col, 'coef': coef[col]} for col in AUDIO]
        print(f'Fit the q={q} regressions')

    return pd.DataFrame(scores), pd.DataFrame(coefs)


def frame(df, rows, model, setup, audio, fold, y_true, y_pred) -> pd.DataFrame:
    """Out-of-fold predictions in the shared schema."""
    return pd.DataFrame(
        {
            'trackID': df['trackID'].iloc[rows].to_numpy(),
            'model': model,
            'setup': setup,
            'audio': audio,
            'fold': np.int8(fold),
            'y_true': y_true,
            'y_pred': y_pred,
        }
    )


def mse(y_true, y_pred) -> float:
    return float(np.mean((np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)) ** 2))


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mse(y_true, y_pred)))


def r2(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    return 1 - mse(y_true, y_pred) / float(np.var(y_true))

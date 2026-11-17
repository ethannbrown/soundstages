import numpy as np
import pandas as pd
import pytest

from folds import assign_between, assign_within, mse, r2, rmse, split, within_target


# Toy table of 23 artists with 3 to 11 tracks each
@pytest.fixture
def toy():
    rng = np.random.default_rng(0)
    uuids = np.repeat([f'a{i}' for i in range(23)], rng.integers(3, 12, 23))
    df = pd.DataFrame({'uuid': pd.Series(uuids).astype('category')})
    df['trackID'] = [f't{i}' for i in range(len(df))]
    df['fold_between'] = assign_between(df['uuid'], 3)
    df['in_within'] = df.groupby('uuid', observed=True)['uuid'].transform('size') >= 5
    df['fold_within'] = pd.Series(pd.NA, index=df.index, dtype='Int8')
    df.loc[df['in_within'], 'fold_within'] = assign_within(df.loc[df['in_within'], 'uuid'], 3)
    return df


def test_between_keeps_artists_out_of_train(toy):
    for _, train, test in split(toy, 'between'):
        assert set(toy['uuid'].iloc[train]).isdisjoint(toy['uuid'].iloc[test])
    assert sorted(toy['fold_between'].unique()) == [0, 1, 2, 3, 4]


def test_within_puts_every_artist_in_every_fold(toy):
    inside = toy[toy['in_within']]
    assert (inside.groupby('uuid', observed=True)['fold_within'].nunique() == 5).all()
    for _, train, test in split(toy, 'within'):
        assert toy['in_within'].iloc[np.concatenate([train, test])].all()


def test_folds_are_seeded(toy):
    again = assign_between(toy['uuid'], 3)
    pd.testing.assert_series_equal(toy['fold_between'], again, check_names=False)


def test_within_target_uses_training_rows_only():
    # Artist 0: train 2, 4 (mean 3), test 10. Artist 1: train 5 (mean 5), test 1.
    y = np.array([2.0, 4.0, 10.0, 5.0, 1.0])
    groups = np.array([0, 0, 0, 1, 1])
    train, test = np.array([0, 1, 3]), np.array([2, 4])
    y_train, y_test = within_target(y, groups, train, test)
    np.testing.assert_allclose(y_train, [-1, 1, 0])
    np.testing.assert_allclose(y_test, [7, -4])

    # Changing a test row moves only that row
    y[2] = 100.0
    _, y_test = within_target(y, groups, train, test)
    np.testing.assert_allclose(y_test, [97, -4])


def test_metrics_on_known_values():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r2(y, y) == 1
    assert rmse(y, y) == 0
    assert r2(y, np.full(4, y.mean())) == 0
    assert mse(y, [2.0, 2.0, 2.0, 2.0]) == pytest.approx(1.5)
    assert rmse([0.0, 0.0], [3.0, 4.0]) == pytest.approx(np.sqrt(12.5))

import shutil
import sys

import pandas as pd

from config import ALBUMS_CLEAN, ARTISTS, BASE, DATASET, TRACKS_CLEAN

# Saves the outputs of the rerunnable stages, then checks reruns against them.
# Usage, from the project root:
#   python reference.py save [name ...]
#   python reference.py check [name ...]
REFS = BASE / 'references'
OUTPUTS = {
    'artists': ARTISTS,
    'albums_clean': ALBUMS_CLEAN,
    'tracks_clean': TRACKS_CLEAN,
    'dataset': DATASET,
}

action = sys.argv[1] if len(sys.argv) > 1 else ''
names = sys.argv[2:] or list(OUTPUTS)
unknown = [name for name in names if name not in OUTPUTS]
if action not in ('save', 'check') or unknown:
    print(f'Usage: python reference.py save|check [{" ".join(OUTPUTS)}]')
    sys.exit(1)

if action == 'save':
    REFS.mkdir(exist_ok=True)
    for name in names:
        ref = REFS / f'{name}.parquet'

        # A reference is never overwritten; delete it by hand to replace it
        if ref.exists():
            print(f'Skipped {name} because a reference already exists')
            continue

        shutil.copy2(OUTPUTS[name], ref)
        df = pd.read_parquet(ref)
        lines = [f'rows: {len(df)}', 'columns:'] + [f'{col} {dtype}' for col, dtype in df.dtypes.items()]
        (REFS / f'{name}.txt').write_text('\n'.join(lines) + '\n')
        print(f'Saved {name} with {len(df):,} rows and {df.shape[1]} columns')

if action == 'check':
    failed = False
    for name in names:
        ref = REFS / f'{name}.parquet'
        if not ref.exists():
            print(f'{name} has no reference to check against')
            failed = True
            continue

        try:
            pd.testing.assert_frame_equal(pd.read_parquet(OUTPUTS[name]), pd.read_parquet(ref))
            print(f'{name} matches its reference')
        except AssertionError as e:
            print(f'{name} differs from its reference: {e}')
            failed = True

    sys.exit(1 if failed else 0)

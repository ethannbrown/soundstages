import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

CLEAN_TRACKS = (
    Path(__file__).resolve().parent.parent / 'src' / 'prepare' / 'clean_tracks.py'
)


# clean_tracks.py is a flat script, so importing it would run the stage and
# overwrite tracks_clean.parquet. Instead, run only its imports, UPPERCASE
# constants and functions.
# Session 2 moves these into text.py, and this becomes a plain import.
def load_rules():
    tree = ast.parse(CLEAN_TRACKS.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.FunctionDef)):
            keep.append(node)
        elif isinstance(node, ast.Assign) and all(
            isinstance(t, ast.Name) and t.id.isupper() for t in node.targets
        ):
            keep.append(node)

    namespace = {}
    exec(
        compile(ast.Module(keep, type_ignores=[]), str(CLEAN_TRACKS), 'exec'), namespace
    )
    return SimpleNamespace(**namespace)


@pytest.fixture(scope='module')
def rules():
    return load_rules()

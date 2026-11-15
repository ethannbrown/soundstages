import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

PREPARE = Path(__file__).resolve().parent.parent / 'src' / 'prepare'


# The cleaning stages are flat scripts, so importing one would run the stage and
# overwrite its output. Instead, run only its imports, UPPERCASE constants and
# functions.
# Session 2 moves these into text.py, and this becomes a plain import.
def load_rules(script):
    path = PREPARE / script
    tree = ast.parse(path.read_text())
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.FunctionDef)):
            keep.append(node)
        elif isinstance(node, ast.Assign) and all(
            isinstance(t, ast.Name) and t.id.isupper() for t in node.targets
        ):
            keep.append(node)

    namespace = {}
    exec(compile(ast.Module(keep, type_ignores=[]), str(path), 'exec'), namespace)
    return SimpleNamespace(**namespace)


@pytest.fixture(scope='module')
def rules():
    return load_rules('clean_tracks.py')


@pytest.fixture(scope='module')
def album_rules():
    return load_rules('clean_albums.py')

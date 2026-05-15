# mindful

A command-line meditation companion. Single-user, local-only, no network.
All data stored in `~/.mindful/` as JSON files.

## Commands (intended)

- `mindful start --duration N --mode M` — start a meditation session
- `mindful note "text"` — annotate the most recent session
- `mindful stats` — show streak, total minutes, completion rate
- `mindful history --last N` — list recent sessions
- `mindful config --bell-sound X` — adjust preferences

See `docs/spec.md` for full specification.

## Running the tests

The `mindful` package must be installed into a virtualenv before `pytest`
can import it. Invoking the system `pytest` (often a pyenv shim) from a
fresh clone fails with `ModuleNotFoundError: No module named 'mindful'`.

The supported workflow is:

```bash
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pip install pytest
.venv/bin/pytest tests/smoke/ -x        # fast smoke run (L3 integration)
.venv/bin/pytest                        # full suite
```

Equivalently, with the venv activated:

```bash
source .venv/bin/activate
python -m pytest tests/smoke/ -x
```

Either form puts the editable `mindful` install on the path that `pytest`
actually uses. `tests/smoke/test_smoke.py` documents the same contract in
code via its `_mindful_invocation()` helper.

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

# Project rules

## Package manager: `uv`, always

Dependencies live in `pyproject.toml` with a committed `uv.lock`. Add them with `uv add` (or
`uv add --dev`), **never** `pip install`. Every command runs through `uv run` — there is no
activate-the-venv step, and no command in this repo should assume an ambient interpreter.

```bash
uv sync                                   # install
uv run python manage.py migrate
uv run python manage.py seed_demo         # demo household, dates relative to today
uv run python manage.py runserver
uv run pytest
```

## Where the logic lives

`chores/recurrence.py` is the one piece of real logic and is **pure** — dates in, a date out, no ORM
imports, no notion of "now". Keep it that way: it is the reason the rules can be tested
exhaustively without a database. Anything needing the clock takes a date argument.

`chores/dates.py` is the single source of "what day is it": `today()` over `timezone.localdate()`.
Never call `date.today()` — it ignores `TIME_ZONE`, and tests freeze the clock by patching this seam.

## Two rules that are easy to break

**Advancing a chore is a compare-and-swap, not a save.** `select_for_update()` is a no-op on SQLite
(`has_select_for_update` is `False`), so the row lock does not protect the read-modify-write. The
`UPDATE` is filtered on the `next_due` that was read, so concurrent claims cannot both land. See
`_record` in `chores/views.py` and `TestConcurrentClaims`.

**Deleting a chore is soft** (`is_active = False`). History must survive; anything listing chores
filters on `is_active=True`.

## Scope

[SPEC.md](SPEC.md) is the standing reference, including what is deliberately **out of scope**
(notifications, fairness scoring, rotation, multi-household, real accounts). Check it before adding a
feature. [backlog.md](backlog.md) tracks implementation state.

## Tests

`tests/` at the project root, not per-app. `tests/conftest.py` freezes `today` for every test
automatically. The recurrence rules carry the bulk of the value — add cases there first.

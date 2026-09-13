# Household Chores — Recurring Reminder Board

A small Django app that answers one question for a shared household: **what needs doing right now?**

It is a recurring-due engine, not a fairness or rotation tool. Chores sit in a shared pool, nobody is
assigned anything, and whoever does one claims it. See [SPEC.md](SPEC.md) for the full scope.

## Quick start

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo     # a demo household, dated relative to today
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/, pick a name, and the board shows what is overdue.

## Tests

```bash
uv run pytest
```

49 tests. The bulk of them cover the recurrence rules directly, with no database.

## What it does

| Route | |
|---|---|
| `/` | The board: **Overdue** (most late first, with day counts), **Due today**, **Next 14 days** |
| `/who/` | Pick your name. No password — it only decides whose name lands on a completion |
| `/history/` | Everything done or skipped, newest first, labelled late / on time / skipped |
| `/chores/` | Add, edit and remove chores |
| `/admin/` | The Django admin, for anything the UI does not cover |

**Done** records who did it and advances the schedule. **Skip** advances the schedule identically but
credits nobody — it means "this occurrence is not happening", not "this is done".

## How recurrence works

Each chore picks one of two modes plus an interval:

- **Interval since last done** — `next_due = completed_on + interval_days`. "Vacuum every 7 days"
  means seven days after you last vacuumed, whenever that was.
- **Fixed schedule** — a calendar slot that does not drift. The due date advances by whole intervals
  until it is strictly in the future, so doing a chore late does not drag the schedule along behind
  it, and doing one early still moves it to the next slot.

A weekly bin day due Monday, done on Wednesday, is next due the following Monday — not Wednesday.
[SPEC.md](SPEC.md) has the worked tables.

## Layout

```
config/                 Django project — settings, urls, wsgi/asgi
chores/
  recurrence.py         the recurrence rules — pure, no ORM, no clock
  dates.py              today(), the one place the clock is read
  models.py             Housemate, Chore, Completion
  views.py              board, identity, claim/skip, history, CRUD
  identity.py           session identity
  management/commands/  seed_demo
templates/              board, who, history, chore CRUD
static/css/app.css      one stylesheet, no build step
tests/                  pytest suite
```

## Stack

Django 6, SQLite, server-rendered Django templates with no frontend build step, pytest +
pytest-django, and [uv](https://docs.astral.sh/uv/) as the package manager — always `uv add` /
`uv run`, never bare `pip` or an activated venv.

## Time zone

Every "is this due today?" question is answered against `TIME_ZONE` in
[config/settings.py](config/settings.py), currently `Europe/Riga`. Change it if the household lives
elsewhere.

# Household Chores — Recurring Reminder Board

A small Django app that answers one question for a shared household: **what needs doing right now?**

It is a recurring-due engine, not a fairness or rotation tool — chores sit in a shared pool, and
whoever does one claims it. See [SPEC.md](SPEC.md) for the full scope and [backlog.md](backlog.md)
for the implementation plan.

## Status

Work in progress.

- ✅ Spec written ([SPEC.md](SPEC.md))
- ✅ Project settings, pytest + pytest-django wiring
- ✅ Domain models and initial migration
- ⬜ Recurrence engine, board, claim/skip, history, chore CRUD, seed data

## Stack

- Django 6 + SQLite
- Server-rendered Django templates, minimal vanilla JS, no frontend build step
- pytest + pytest-django
- [uv](https://docs.astral.sh/uv/) as the package manager — always `uv add` / `uv run`, never bare
  `pip` or an activated venv

## Setup

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

The Django admin at `/admin/` already manages all three models; create a superuser with
`uv run python manage.py createsuperuser`. The board UI and `seed_demo` command are still to come.

## Tests

```bash
uv run pytest
```

## Domain model

One `Chore` row carries only its **next** occurrence — there is no table of pre-generated future
occurrences, which keeps "what's due" a single ordered query. History lives in `Completion`.

| Model | Purpose |
|---|---|
| `Housemate` | A name that can claim a chore. No accounts, no passwords |
| `Chore` | Name, notes, recurrence mode, `interval_days`, `next_due` |
| `Completion` | One occurrence, done or skipped, with the due date snapshotted |

Each chore recurs in one of two modes:

- **`INTERVAL`** — `next_due = completed_on + interval_days`. "Vacuum every 7 days" means seven days
  after you last vacuumed.
- **`FIXED`** — a calendar schedule that does not drift: advance by whole `interval_days` steps until
  strictly after the completion date. Doing a chore late does not drag the schedule with it.

**Skip** advances the schedule exactly like a completion, but credits nobody.

## Layout

```
config/      Django project — settings, urls, wsgi/asgi
chores/      The app — models, migrations, (recurrence engine, views, forms to come)
templates/   Project-level templates
static/css/  One small stylesheet
tests/       pytest suite
```

## Time zone

Every "is this due today?" question is answered against `TIME_ZONE` in
[config/settings.py](config/settings.py), currently `Europe/Riga`. Change it there if the household
lives elsewhere.

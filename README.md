# Household Chores — Recurring Reminder Board

A small Django app that answers one question for a shared household: **what needs doing right now?**

It is a recurring-due engine, not a fairness or rotation tool — chores sit in a shared pool, and
whoever does one claims it. See [_docs/plan.md](_docs/plan.md) for the full scope and design.

## Status

Scoping complete; implementation not yet started.

## Stack

- Django 5 + SQLite
- Server-rendered templates, minimal vanilla JS
- pytest + pytest-django
- [uv](https://docs.astral.sh/uv/) as the package manager — always `uv add` / `uv run`, never bare
  `pip` or an activated venv

## Setup (once implemented)

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

## Tests

```bash
uv run pytest
```

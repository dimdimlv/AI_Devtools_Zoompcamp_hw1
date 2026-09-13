# Household Chores — Recurring Reminder Board (Django)

## Context

A shared household needs one place that answers "what needs doing right now?" The repo
(`/Users/dmitry/Projects/AI_Devtools_Zoompcamp_hw1`) is empty — this is a greenfield homework project.

Scope decided in conversation:

- **Core job:** a recurring-due engine. The tool knows what's due and surfaces it. It is *not* a fairness
  engine, a rotation, or a points ledger.
- **Delivery:** a web page housemates check. No push notifications, no background scheduler.
- **Assignment:** none. Due chores sit in a shared pool; whoever does one claims it.
- **Recurrence:** per-chore choice between a fixed calendar schedule and an interval measured from the
  last completion.
- **Identity:** pick your name from a list, no login. Single household.
- **Done means:** runs locally with seed data, plus tests over the recurrence rules.

## Stack

Django 5 + SQLite + Django templates (server-rendered, minimal vanilla JS). pytest + pytest-django.
No frontend build step.

**Package manager: `uv`, always.** Dependencies live in `pyproject.toml` with a committed `uv.lock`;
they are added with `uv add`, never `pip install`. Every command in the README, the docs, and any
future tooling runs through `uv run` (`uv run python manage.py …`, `uv run pytest`) so there is no
activate-the-venv step and no ambient-interpreter drift. This is recorded as a project rule in
`CLAUDE.md` so it survives into later sessions.

## Domain model (`chores/models.py`)

```
Housemate    name, is_active, created_at
Chore        name, notes, recurrence (FIXED|INTERVAL), interval_days (PositiveInt),
             next_due (DateField), is_active, created_at
Completion   chore (FK, related_name="completions"), housemate (FK, null=True on delete),
             due_date (the date this occurrence was due — snapshotted),
             completed_on (DateField), created_at, was_skipped (Bool)
```

One `Chore` row carries only its *next* occurrence; history lives in `Completion`. No pre-generated
occurrence table — it keeps the model small and makes "what's due" a single ordered query.

`Chore` helpers: `is_overdue(today)`, `days_late(today)`, `status(today)` → `overdue` / `due_today` /
`upcoming`.

## Recurrence engine (`chores/recurrence.py`)

The one piece of real logic; keep it a pure function over `date`s with no ORM imports so it is
trivially testable:

```python
def next_due_date(recurrence, current_due, completed_on, interval_days) -> date
```

- `INTERVAL` → `completed_on + interval_days`. ("Vacuum every 7 days" — the calendar day doesn't matter.)
- `FIXED` → advance `current_due` by whole `interval_days` steps until strictly after `completed_on`.
  A chore done late does not drag the schedule; a chore done early still moves to the next slot.
- Skipping uses the same function with `completed_on = today`, so a skipped occurrence advances the
  schedule exactly like a completed one.

Guard `interval_days >= 1` at the model level (validator) so the advance loop always terminates.

## Views & URLs (`chores/views.py`, `chores/urls.py`)

| Route | Purpose |
|---|---|
| `/` | Board: **Overdue** (sorted most-late first, "3 days late"), **Due today**, **Upcoming** (next 14 days). Header shows current housemate + count of overdue items. |
| `/who/` | Name picker. Writes `housemate_id` into the Django session; a context processor exposes `current_housemate` to every template. |
| `POST /chores/<pk>/done/` | Record a `Completion`, advance `next_due`. Redirect back to `/`. |
| `POST /chores/<pk>/skip/` | Same, `was_skipped=True`. |
| `/history/` | Reverse-chronological completion log: chore, who, when, late/on-time/skipped. Paginated. |
| `/chores/`, `/chores/new/`, `/chores/<pk>/edit/`, `/chores/<pk>/delete/` | In-app CRUD via a `ChoreForm` (ModelForm). Delete is a soft `is_active=False` so history stays intact. |

Both mutating actions run inside `transaction.atomic()` and re-read the chore with `select_for_update()`,
so two housemates clicking "Done" at the same moment produce one completion and one advance, not two.
Anyone without a session identity is redirected to `/who/` before they can claim.

Dates come from `django.utils.timezone.localdate()` everywhere — never `date.today()` — with
`TIME_ZONE` set to the household's zone and `USE_TZ = True`.

## Files to create

```
manage.py
config/            settings.py, urls.py, wsgi.py, asgi.py
chores/            models.py, recurrence.py, views.py, urls.py, forms.py, admin.py,
                   context_processors.py, migrations/, management/commands/seed_demo.py
templates/         base.html, board.html, who.html, history.html,
                   chore_list.html, chore_form.html, chore_confirm_delete.html
static/css/app.css   (one small stylesheet: overdue = red accent, due-today = amber, upcoming = muted)
tests/             test_recurrence.py, test_views.py
pyproject.toml     deps + pytest-django config
uv.lock            committed
SPEC.md            the full agreed scope (see below)
CLAUDE.md          project rules — uv only, where the recurrence logic lives, run/test commands
README.md          setup, run, seed, test — all commands via `uv run`
```

`SPEC.md` is written **first**, before any code, and holds everything settled in this conversation as
the standing reference: the core job (recurring-due engine, not a rotation or points ledger), the
shared-pool claim model with no assignment, both recurrence modes with the late/early examples spelled
out, the no-login identity model, the v1 feature list, and what is explicitly **out of scope** —
push notifications, fairness scoring, rotation, multi-household, real accounts. Decisions ruled out
are recorded as such, so the boundary is as legible as the feature list.

`admin.py` registers all three models — a free management backdoor alongside the in-app CRUD.

`seed_demo.py` creates 3 housemates and ~8 realistic chores spanning both recurrence modes and
deliberately straddling the boundaries: a couple overdue, one due today, the rest upcoming.

## Tests

`tests/test_recurrence.py` — pure, no DB, the bulk of the value:

- INTERVAL: done on time, done late, done early → always `completed_on + interval`.
- FIXED: done on the due date → +1 interval.
- FIXED: done 9 days late on a 7-day chore → advances **two** steps, lands strictly in the future.
- FIXED: done early → next slot, schedule unshifted.
- Interval of 1 day, and a very late completion (months), terminate correctly.

`tests/test_views.py` — Django test client:

- Claiming a due chore writes a `Completion` with the right `due_date` snapshot and advances `next_due`.
- Skipping sets `was_skipped` and advances identically.
- Board groups and orders correctly for a fixed "today" (freeze via a `today` helper the views call, so
  tests can monkeypatch it).
- Claiming without a session identity redirects to `/who/`.

## Verification

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
uv run pytest
```

Then, in the browser: pick a name → the board shows overdue items first with day counts → click **Done**
on an overdue chore → it disappears from Overdue and reappears under Upcoming with a correctly advanced
date → `/history/` shows the entry with your name → **Skip** on another chore advances it without
crediting anyone → add a chore via `/chores/new/` and confirm it lands in the right board section.

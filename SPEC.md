# Household Chores — Recurring Reminder Board

The standing reference for what this project is and is not. Implementation tasks live in
[backlog.md](backlog.md); the original design notes are in [_docs/plan.md](_docs/plan.md).

## Core job

One page that answers **"what needs doing right now?"** for a single shared household.

The app is a **recurring-due engine**. It knows when each chore is next due, surfaces what is overdue
or due today, and advances the schedule when someone does the chore. That is the whole job.

It is explicitly **not** a fairness engine, a rotation, or a points ledger. It does not decide *who*
should do anything.

## Identity

Pick your name from a list. No login, no passwords, no accounts. The choice is stored in the Django
session and shown in the page header. One household per deployment.

A housemate without a session identity can read the board but is redirected to the name picker before
claiming anything.

## Assignment: none

Due chores sit in a **shared pool**. Nobody is assigned a chore; whoever does one claims it by
clicking **Done**, and the completion records their name. Claiming is a record of what happened, not
a fulfilment of an obligation.

## Recurrence

Each chore chooses one of two modes, plus an `interval_days` (always ≥ 1).

### `INTERVAL` — measured from the last completion

`next_due = completed_on + interval_days`

The calendar day does not matter. "Vacuum every 7 days" means seven days after you last vacuumed,
whenever that was.

| Chore | Due | Completed | New due |
|---|---|---|---|
| Vacuum, every 7 days | Mar 10 | Mar 10 (on time) | Mar 17 |
| Vacuum, every 7 days | Mar 10 | Mar 13 (3 days late) | Mar 20 |
| Vacuum, every 7 days | Mar 10 | Mar 8 (2 days early) | Mar 15 |

### `FIXED` — a calendar schedule that does not drift

Advance `current_due` by whole `interval_days` steps until it is **strictly after** `completed_on`.

A chore done late does not drag the schedule with it; a chore done early still moves on to the next
slot rather than collapsing back.

| Chore | Due | Completed | New due |
|---|---|---|---|
| Bins out, every 7 days | Mar 10 | Mar 10 (on time) | Mar 17 |
| Bins out, every 7 days | Mar 10 | Mar 19 (9 days late) | Mar 24 (two steps — strictly future) |
| Bins out, every 7 days | Mar 10 | Mar 8 (2 days early) | Mar 17 (unshifted) |

### Skipping

**Skip** advances the schedule exactly as a completion does — the same function, with
`completed_on = today` — but records `was_skipped = True` and credits nobody. It means "this
occurrence is not happening", not "this chore is done".

## Data model

One `Chore` row carries only its **next** occurrence. History lives in `Completion`. There is no
pre-generated table of future occurrences, which keeps "what's due" a single ordered query.

```
Housemate    name, is_active, created_at
Chore        name, notes, recurrence (FIXED|INTERVAL), interval_days (≥ 1),
             next_due (date), is_active, created_at
Completion   chore (FK), housemate (FK, nullable), due_date (snapshot of the occurrence's due date),
             completed_on (date), was_skipped (bool), created_at
```

`due_date` is snapshotted on the completion so history stays truthful after the chore's schedule moves
on — or after the chore itself is edited.

Deleting a chore is a **soft delete** (`is_active = False`) so its history survives.

## v1 feature list

| Route | What it does |
|---|---|
| `/` | The board: **Overdue** (most-late first, with day counts), **Due today**, **Upcoming** (next 14 days) |
| `/who/` | Name picker; writes the identity into the session |
| `POST /chores/<pk>/done/` | Record a completion, advance `next_due` |
| `POST /chores/<pk>/skip/` | Same, credited to nobody, marked skipped |
| `/history/` | Reverse-chronological log: chore, who, when, late / on-time / skipped. Paginated |
| `/chores/…` | In-app CRUD — list, new, edit, soft delete |

Both mutating actions run inside a transaction and re-read the chore with `select_for_update()`, so
two housemates clicking **Done** at the same moment produce one completion and one advance, not two.

All dates come from `django.utils.timezone.localdate()` behind a `today()` helper — never
`date.today()` — with `TIME_ZONE` set to the household's zone and `USE_TZ = True`. Views call the
helper so tests can freeze "today".

## Out of scope

These were considered and **ruled out** for v1. They are not "not yet"; they are boundary markers.

- **Push notifications, email, background schedulers.** The board is pull-based: housemates check it.
  Nothing runs when nobody is looking at the page.
- **Fairness scoring, points, leaderboards.** Not the job. `/history/` records who did what; it draws
  no conclusions from that.
- **Rotation or assignment.** The shared pool is the model. No "it's your turn".
- **Multi-household / tenancy.** One household per deployment.
- **Real user accounts, passwords, permissions.** Name-picker identity only. Anyone who can reach the
  page is trusted.

## Stack

Django 6 + SQLite + Django templates, server-rendered with minimal vanilla JS and no frontend build
step. pytest + pytest-django.

**Package manager: `uv`, always.** Dependencies live in `pyproject.toml` with a committed `uv.lock`,
added with `uv add` — never `pip install`. Every command runs through `uv run`, so there is no
activate-the-venv step and no ambient-interpreter drift.

## Done means

Runs locally with seed data, and the recurrence rules are covered by tests.

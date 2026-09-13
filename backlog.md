# Backlog — Household Chores board

Derived from [_docs/plan.md](_docs/plan.md). Tasks are ordered; each one is a commit-sized slice that
leaves the repo working. All commands run through `uv run`.

**Already done:** Django project (`config/`) + empty `chores/` app registered in `INSTALLED_APPS`,
`uv` project with `uv.lock`, README, `.gitignore`.

---

## T1 — Write SPEC.md ✅

Move the agreed scope out of `_docs/plan.md` into a standing `SPEC.md` at the repo root: core job
(recurring-due engine), shared-pool claim model, both recurrence modes with the late/early examples,
no-login identity, the v1 feature list, and the explicit **out of scope** list (push notifications,
fairness scoring, rotation, multi-household, real accounts).

*Done when:* `SPEC.md` exists and the plan's decisions — including the ruled-out ones — are readable
without the conversation.

## T2 — Project settings & tooling ✅

- `TIME_ZONE` → household zone (currently `'UTC'`), keep `USE_TZ = True`.
- `TEMPLATES['DIRS']` → project-level `templates/`; add `STATICFILES_DIRS` for `static/`.
- `uv add --dev pytest pytest-django`; pytest config (`DJANGO_SETTINGS_MODULE`, `testpaths = tests`) in
  `pyproject.toml`.
- Decide the Django version: `pyproject.toml` pins `django>=6.1.1`, the plan says Django 5.
  **Resolved: Django 6** — it is what is installed and what the project was scaffolded with; SPEC and
  README say Django 6. `_docs/plan.md` is left as the historical design note.
- `TIME_ZONE` **resolved: `Europe/Riga`** (the machine's zone).
- Delete the unused `chores/tests.py` stub in favour of `tests/`.

*Done when:* `uv run pytest` collects zero tests and exits clean; `uv run python manage.py check` passes.

## T3 — Models + migration ✅

`Housemate`, `Chore`, `Completion` exactly as in the plan. `interval_days` gets a
`MinValueValidator(1)` so the FIXED advance loop always terminates. `Completion.housemate` is
nullable with `on_delete=SET_NULL`.

*Done when:* migration applies on a fresh DB; a `Chore` with `interval_days=0` fails `full_clean()`.

## T4 — Recurrence engine + tests ✅

`chores/recurrence.py` with `next_due_date(recurrence, current_due, completed_on, interval_days) -> date`
— pure, no ORM imports. `tests/test_recurrence.py` covers: INTERVAL on time / late / early;
FIXED on the due date; FIXED 9 days late on a 7-day chore (advances two steps, lands strictly in the
future); FIXED done early; `interval_days=1`; a months-late completion.

*Done when:* `uv run pytest tests/test_recurrence.py` is green. This is the bulk of the test value —
write it before any view code.

## T5 — Chore status helpers ✅

`Chore.is_overdue(today)`, `days_late(today)`, `status(today)` → `overdue` / `due_today` / `upcoming`.
A `chores/dates.py` (or similar) `today()` wrapper over `timezone.localdate()` that every view calls,
so tests can monkeypatch a fixed date.

*Done when:* helpers are unit-tested against a frozen `today`.

## T6 — Identity: `/who/` + context processor ✅

Name picker listing active housemates; selection writes `housemate_id` into the session.
`chores/context_processors.py` exposes `current_housemate` to every template (registered in settings).

*Done when:* picking a name persists across requests; a stale/deleted `housemate_id` degrades to "no
identity" rather than erroring.

## T7 — Board view `/` ✅

Three groups: **Overdue** (most-late first, "3 days late"), **Due today**, **Upcoming** (next 14 days).
Header shows the current housemate and the overdue count. Templates `base.html` + `board.html`.

*Done when:* the board renders from seed data with correct grouping and ordering for a frozen `today`.

## T8 — Claim & skip actions ✅

`POST /chores/<pk>/done/` and `POST /chores/<pk>/skip/`. Each runs in `transaction.atomic()` and
re-reads the chore with `select_for_update()`, writes a `Completion` (snapshotting `due_date`,
`was_skipped` for skip), advances `next_due` via T4, and redirects to `/`. No session identity →
redirect to `/who/` without mutating anything.

*Done when:* `tests/test_views.py` covers claim, skip, the `due_date` snapshot, the advance, and the
anonymous redirect. Two concurrent "Done" clicks must yield one completion and one advance.

## T9 — Seed command ✅

`chores/management/commands/seed_demo.py`: 3 housemates and ~8 realistic chores across both recurrence
modes, deliberately straddling the boundaries — a couple overdue, one due today, the rest upcoming.
Idempotent enough to re-run.

*Done when:* `uv run python manage.py seed_demo` on a fresh DB produces a board with all three sections
populated.

## T10 — History `/history/` ✅

Reverse-chronological completion log — chore, who, when, late / on-time / skipped — paginated.
`select_related` on chore and housemate to keep it to one query per page.

*Done when:* completions from T8 appear with the acting housemate's name and the right label.

## T11 — Chore CRUD ✅

`/chores/`, `/chores/new/`, `/chores/<pk>/edit/`, `/chores/<pk>/delete/` via a `ChoreForm` ModelForm.
Delete is a soft `is_active=False` so history survives. (Admin registration for all three models is
already done — it landed early so there was something to inspect before the board existed.)

*Done when:* a chore added through the UI lands in the correct board section; a deleted chore leaves
`/history/` intact.

## T12 — Styling ✅

One small `static/css/app.css`: overdue = red accent, due-today = amber, upcoming = muted. No build step.

*Done when:* the three board sections are distinguishable at a glance.

## T13 — CLAUDE.md + README ✅

`CLAUDE.md`: uv-only rule, where the recurrence logic lives, run/test commands. README updated from
"not yet started" to real setup / run / seed / test instructions.

*Done when:* a fresh clone can follow the README end to end.

## T14 — Verification pass ✅

Run the plan's checklist: `uv sync` → `migrate` → `seed_demo` → `runserver` → `pytest`, then in the
browser: pick a name → overdue-first board with day counts → **Done** on an overdue chore moves it to
Upcoming with an advanced date → `/history/` shows the entry → **Skip** advances without crediting
anyone → a new chore from `/chores/new/` lands in the right section.

*Done when:* every step passes on a fresh database.

**Verified.** `uv sync` → `migrate` → `seed_demo` → `pytest` (49 passing) all run clean on a database
deleted and rebuilt from scratch; every route returns 200 and the claim/skip flow was driven against
the running server, not just the test client.

---

### Out of scope for this backlog

Push notifications, background schedulers, fairness/points scoring, rotation or assignment,
multi-household support, real user accounts.

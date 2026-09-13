"""The recurrence engine.

Deliberately pure: dates in, a date out, no ORM imports and no notion of "now".
Everything else in the project can be exercised through the Django test client,
but this is the piece worth testing exhaustively, so it stays trivially callable.
"""

from datetime import date, timedelta

FIXED = 'FIXED'
INTERVAL = 'INTERVAL'


def next_due_date(recurrence, current_due, completed_on, interval_days):
    """Return the date an occurrence becomes due again.

    ``INTERVAL`` counts from the completion: "every 7 days" means seven days
    after you last did it, whenever that was.

    ``FIXED`` keeps a calendar schedule that does not drift: advance
    ``current_due`` by whole ``interval_days`` steps until it lands strictly
    after ``completed_on``. Doing a chore late does not drag the schedule along
    behind it, and doing one early still moves it on to the next slot.

    Skipping calls this with ``completed_on=today``, so a skipped occurrence
    advances exactly like a completed one.
    """
    if interval_days < 1:
        raise ValueError(f'interval_days must be at least 1, got {interval_days!r}')

    step = timedelta(days=interval_days)

    if recurrence == INTERVAL:
        return completed_on + step

    if recurrence != FIXED:
        raise ValueError(f'unknown recurrence {recurrence!r}')

    # Whole steps from current_due to strictly past completed_on. Computed
    # rather than looped so a chore left undone for years costs the same as one
    # done on time.
    behind = (completed_on - current_due).days
    if behind < 0:
        steps = 1
    else:
        steps = behind // interval_days + 1
    return current_due + steps * step

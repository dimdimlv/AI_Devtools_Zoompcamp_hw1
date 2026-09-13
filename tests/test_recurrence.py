"""The recurrence rules, exhaustively. No database, no Django test client."""

from datetime import date, timedelta

import pytest

from chores.recurrence import FIXED, INTERVAL, next_due_date


class TestInterval:
    """INTERVAL always counts from the completion; the calendar is irrelevant."""

    def test_done_on_time(self):
        assert next_due_date(INTERVAL, date(2026, 3, 10), date(2026, 3, 10), 7) == date(2026, 3, 17)

    def test_done_late(self):
        assert next_due_date(INTERVAL, date(2026, 3, 10), date(2026, 3, 13), 7) == date(2026, 3, 20)

    def test_done_early(self):
        assert next_due_date(INTERVAL, date(2026, 3, 10), date(2026, 3, 8), 7) == date(2026, 3, 15)

    def test_current_due_is_ignored_entirely(self):
        completed = date(2026, 3, 13)
        for due in (date(2020, 1, 1), date(2026, 3, 13), date(2030, 12, 31)):
            assert next_due_date(INTERVAL, due, completed, 7) == date(2026, 3, 20)


class TestFixed:
    """FIXED keeps its slots; a late completion must not drag the schedule."""

    def test_done_on_the_due_date_advances_one_interval(self):
        assert next_due_date(FIXED, date(2026, 3, 10), date(2026, 3, 10), 7) == date(2026, 3, 17)

    def test_done_nine_days_late_on_a_weekly_chore_advances_two_steps(self):
        # Mar 17 has already passed, so one step is not enough.
        result = next_due_date(FIXED, date(2026, 3, 10), date(2026, 3, 19), 7)
        assert result == date(2026, 3, 24)
        assert result > date(2026, 3, 19), 'must land strictly in the future'

    def test_done_early_leaves_the_schedule_unshifted(self):
        assert next_due_date(FIXED, date(2026, 3, 10), date(2026, 3, 8), 7) == date(2026, 3, 17)

    def test_done_exactly_one_interval_late_advances_two_steps(self):
        # Boundary: completed_on lands exactly on the next slot, which is not
        # strictly after it, so the schedule moves one slot further.
        assert next_due_date(FIXED, date(2026, 3, 10), date(2026, 3, 17), 7) == date(2026, 3, 24)

    def test_result_is_always_strictly_after_the_completion(self):
        due = date(2026, 3, 10)
        for days_late in range(0, 60):
            completed = date(2026, 3, 10) + timedelta(days=days_late)
            assert next_due_date(FIXED, due, completed, 7) > completed


class TestEdgeCases:
    def test_daily_chore(self):
        assert next_due_date(FIXED, date(2026, 3, 10), date(2026, 3, 10), 1) == date(2026, 3, 11)
        assert next_due_date(INTERVAL, date(2026, 3, 10), date(2026, 3, 10), 1) == date(2026, 3, 11)

    def test_daily_chore_months_late_terminates_and_lands_tomorrow(self):
        result = next_due_date(FIXED, date(2026, 3, 10), date(2026, 9, 13), 1)
        assert result == date(2026, 9, 14)

    def test_weekly_chore_months_late(self):
        # Mar 10 + 27 weeks = Sep 15, the first slot strictly after Sep 13.
        assert next_due_date(FIXED, date(2026, 3, 10), date(2026, 9, 13), 7) == date(2026, 9, 15)

    def test_fixed_crosses_a_leap_day(self):
        assert next_due_date(FIXED, date(2028, 2, 27), date(2028, 2, 27), 3) == date(2028, 3, 1)

    def test_interval_of_zero_is_rejected(self):
        with pytest.raises(ValueError, match='at least 1'):
            next_due_date(FIXED, date(2026, 3, 10), date(2026, 3, 10), 0)

    def test_unknown_recurrence_is_rejected(self):
        with pytest.raises(ValueError, match='unknown recurrence'):
            next_due_date('WEEKLY', date(2026, 3, 10), date(2026, 3, 10), 7)

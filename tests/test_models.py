from datetime import date

import pytest
from django.core.exceptions import ValidationError

from chores.models import Chore, Completion, Housemate, Recurrence


@pytest.mark.django_db
def test_interval_days_must_be_at_least_one():
    chore = Chore(
        name='Vacuum',
        recurrence=Recurrence.INTERVAL,
        interval_days=0,
        next_due=date(2026, 3, 10),
    )
    with pytest.raises(ValidationError) as exc:
        chore.full_clean()
    assert 'interval_days' in exc.value.message_dict


@pytest.mark.django_db
def test_completion_survives_its_housemate():
    housemate = Housemate.objects.create(name='Alex')
    chore = Chore.objects.create(
        name='Bins out',
        recurrence=Recurrence.FIXED,
        interval_days=7,
        next_due=date(2026, 3, 10),
    )
    completion = Completion.objects.create(
        chore=chore,
        housemate=housemate,
        due_date=date(2026, 3, 10),
        completed_on=date(2026, 3, 10),
    )

    housemate.delete()

    completion.refresh_from_db()
    assert completion.housemate is None
    assert completion.due_date == date(2026, 3, 10)


class TestChoreStatus:
    """status/days_late/days_until_due against a frozen 'today'."""

    TODAY = date(2026, 9, 13)

    def chore(self, next_due):
        return Chore(
            name='Vacuum',
            recurrence=Recurrence.INTERVAL,
            interval_days=7,
            next_due=next_due,
        )

    def test_past_due_is_overdue(self):
        chore = self.chore(date(2026, 9, 10))
        assert chore.status(self.TODAY) == 'overdue'
        assert chore.is_overdue(self.TODAY)
        assert chore.days_late(self.TODAY) == 3
        assert chore.days_until_due(self.TODAY) == 0

    def test_due_today_is_not_overdue(self):
        chore = self.chore(self.TODAY)
        assert chore.status(self.TODAY) == 'due_today'
        assert not chore.is_overdue(self.TODAY)
        assert chore.days_late(self.TODAY) == 0

    def test_future_is_upcoming(self):
        chore = self.chore(date(2026, 9, 20))
        assert chore.status(self.TODAY) == 'upcoming'
        assert not chore.is_overdue(self.TODAY)
        assert chore.days_late(self.TODAY) == 0
        assert chore.days_until_due(self.TODAY) == 7

    def test_defaults_to_the_real_today(self, monkeypatch):
        monkeypatch.setattr('chores.models.today_', lambda: date(2026, 9, 13))
        assert self.chore(date(2026, 9, 10)).status() == 'overdue'
        assert self.chore(date(2026, 9, 13)).status() == 'due_today'

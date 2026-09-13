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

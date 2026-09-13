from datetime import date, timedelta

import pytest

from chores.models import Chore, Housemate, Recurrence

TODAY = date(2026, 9, 13)


@pytest.fixture
def today():
    return TODAY


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    """Freeze 'today' everywhere the app asks for it.

    Every module reads the clock through chores.dates.today, so the views and
    the context processor are patched by name where they imported it.
    """
    monkeypatch.setattr('chores.dates.today', lambda: TODAY)
    monkeypatch.setattr('chores.views.today_', lambda: TODAY)
    monkeypatch.setattr('chores.context_processors.today', lambda: TODAY)
    monkeypatch.setattr('chores.models.today_', lambda: TODAY)
    return TODAY


@pytest.fixture
def alex(db):
    return Housemate.objects.create(name='Alex')


@pytest.fixture
def make_chore(db):
    def _make(name='Vacuum', recurrence=Recurrence.INTERVAL, interval_days=7, due_offset=0):
        return Chore.objects.create(
            name=name,
            recurrence=recurrence,
            interval_days=interval_days,
            next_due=TODAY + timedelta(days=due_offset),
        )
    return _make


@pytest.fixture
def as_alex(client, alex):
    """A client that has already picked a name."""
    session = client.session
    session['housemate_id'] = alex.pk
    session.save()
    return client

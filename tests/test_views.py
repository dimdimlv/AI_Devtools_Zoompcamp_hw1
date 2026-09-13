from datetime import date, timedelta

import pytest
from django.urls import reverse

from chores.models import Chore, Completion, Housemate, Recurrence

pytestmark = pytest.mark.django_db


class TestClaiming:
    def test_done_records_a_completion_and_advances(self, as_alex, alex, make_chore, today):
        chore = make_chore(recurrence=Recurrence.INTERVAL, interval_days=7, due_offset=-3)

        response = as_alex.post(reverse('chores:done', args=[chore.pk]))

        assert response.status_code == 302
        completion = Completion.objects.get()
        assert completion.chore == chore
        assert completion.housemate == alex
        assert completion.completed_on == today
        # The occurrence that was due, not the one it advanced to.
        assert completion.due_date == today - timedelta(days=3)
        assert not completion.was_skipped

        chore.refresh_from_db()
        assert chore.next_due == today + timedelta(days=7)

    def test_fixed_chore_done_late_does_not_drag_the_schedule(self, as_alex, make_chore, today):
        # Due 9 days ago on a weekly schedule: two steps, landing in the future.
        chore = make_chore(recurrence=Recurrence.FIXED, interval_days=7, due_offset=-9)

        as_alex.post(reverse('chores:done', args=[chore.pk]))

        chore.refresh_from_db()
        assert chore.next_due == today + timedelta(days=5)
        assert chore.next_due > today

    def test_skip_advances_but_credits_nobody(self, as_alex, make_chore, today):
        chore = make_chore(recurrence=Recurrence.INTERVAL, interval_days=7, due_offset=0)

        as_alex.post(reverse('chores:skip', args=[chore.pk]))

        completion = Completion.objects.get()
        assert completion.was_skipped
        assert completion.housemate is None
        assert completion.due_date == today

        chore.refresh_from_db()
        assert chore.next_due == today + timedelta(days=7)

    def test_claiming_without_a_name_redirects_to_the_picker(self, client, make_chore):
        chore = make_chore()

        response = client.post(reverse('chores:done', args=[chore.pk]))

        assert response.status_code == 302
        assert reverse('chores:who') in response['Location']
        # and nothing was mutated on the way out
        assert not Completion.objects.exists()
        original_due = chore.next_due
        chore.refresh_from_db()
        assert chore.next_due == original_due

    def test_get_is_not_allowed(self, as_alex, make_chore):
        chore = make_chore()
        assert as_alex.get(reverse('chores:done', args=[chore.pk])).status_code == 405
        assert not Completion.objects.exists()

    def test_claiming_an_inactive_chore_404s(self, as_alex, make_chore):
        chore = make_chore()
        chore.is_active = False
        chore.save()

        assert as_alex.post(reverse('chores:done', args=[chore.pk])).status_code == 404


class TestBoard:
    def test_groups_and_orders_by_urgency(self, client, make_chore, today):
        make_chore(name='Three days late', due_offset=-3)
        make_chore(name='Ten days late', due_offset=-10)
        make_chore(name='Due now', due_offset=0)
        make_chore(name='Soon', due_offset=5)
        make_chore(name='Beyond the window', due_offset=20)

        context = client.get(reverse('chores:board')).context

        assert [c.name for c in context['overdue']] == ['Ten days late', 'Three days late']
        assert [c.name for c in context['due_today']] == ['Due now']
        assert [c.name for c in context['upcoming']] == ['Soon']

    def test_shows_how_late_things_are(self, client, make_chore):
        make_chore(name='Bins', due_offset=-3)

        response = client.get(reverse('chores:board'))

        assert response.context['overdue'][0].late_days == 3
        assert b'3 days late' in response.content

    def test_inactive_chores_are_hidden(self, client, make_chore):
        chore = make_chore(due_offset=-1)
        chore.is_active = False
        chore.save()

        context = client.get(reverse('chores:board')).context
        assert context['overdue'] == []

    def test_overdue_count_reaches_every_page(self, client, make_chore):
        make_chore(name='a', due_offset=-1)
        make_chore(name='b', due_offset=-2)
        make_chore(name='c', due_offset=3)

        assert client.get(reverse('chores:board')).context['overdue_count'] == 2
        assert client.get(reverse('chores:history')).context['overdue_count'] == 2


class TestIdentity:
    def test_picking_a_name_persists(self, client, alex):
        response = client.post(reverse('chores:who'), {'housemate': alex.pk})

        assert response.status_code == 302
        assert client.session['housemate_id'] == alex.pk
        assert client.get(reverse('chores:board')).context['current_housemate'] == alex

    def test_a_stale_identity_degrades_to_nobody(self, client, alex):
        session = client.session
        session['housemate_id'] = alex.pk
        session.save()
        alex.delete()

        response = client.get(reverse('chores:board'))

        assert response.status_code == 200
        assert response.context['current_housemate'] is None

    def test_a_deactivated_housemate_is_not_offered(self, client, alex):
        alex.is_active = False
        alex.save()

        response = client.get(reverse('chores:who'))

        assert list(response.context['housemates']) == []

    def test_picker_returns_you_to_where_you_were(self, client, alex):
        response = client.post(
            reverse('chores:who'), {'housemate': alex.pk, 'next': '/history/'}
        )
        assert response['Location'] == '/history/'

    def test_picker_refuses_an_offsite_redirect(self, client, alex):
        response = client.post(
            reverse('chores:who'),
            {'housemate': alex.pk, 'next': 'https://example.com/phish'},
        )
        assert response['Location'] == reverse('chores:board')


class TestHistory:
    def test_lists_completions_newest_first_with_labels(self, as_alex, alex, make_chore, today):
        chore = make_chore(name='Bins', due_offset=-2)
        as_alex.post(reverse('chores:done', args=[chore.pk]))

        response = as_alex.get(reverse('chores:history'))

        entry = response.context['page'][0]
        assert entry.chore == chore
        assert entry.housemate == alex
        assert entry.days_late == 2
        assert b'2 days late' in response.content

    def test_history_survives_a_soft_deleted_chore(self, as_alex, make_chore):
        chore = make_chore(name='Bins', due_offset=0)
        as_alex.post(reverse('chores:done', args=[chore.pk]))
        as_alex.post(reverse('chores:chore_delete', args=[chore.pk]))

        response = as_alex.get(reverse('chores:history'))
        assert response.context['page'].paginator.count == 1
        assert b'Bins' in response.content


class TestChoreCrud:
    def test_adding_a_chore_puts_it_on_the_board(self, client, today):
        response = client.post(reverse('chores:chore_new'), {
            'name': 'Mop the floor',
            'notes': '',
            'recurrence': Recurrence.INTERVAL,
            'interval_days': 5,
            'next_due': today.isoformat(),
        })

        assert response.status_code == 302
        chore = Chore.objects.get(name='Mop the floor')
        assert chore.next_due == today

        board = client.get(reverse('chores:board'))
        assert [c.name for c in board.context['due_today']] == ['Mop the floor']

    def test_a_zero_interval_is_rejected(self, client, today):
        response = client.post(reverse('chores:chore_new'), {
            'name': 'Impossible',
            'notes': '',
            'recurrence': Recurrence.FIXED,
            'interval_days': 0,
            'next_due': today.isoformat(),
        })

        assert response.status_code == 200
        assert 'interval_days' in response.context['form'].errors
        assert not Chore.objects.filter(name='Impossible').exists()

    def test_delete_is_soft(self, client, make_chore):
        chore = make_chore(name='Bins')

        client.post(reverse('chores:chore_delete', args=[chore.pk]))

        chore.refresh_from_db()
        assert not chore.is_active
        assert Chore.objects.filter(pk=chore.pk).exists()

    def test_editing_changes_the_schedule(self, client, make_chore, today):
        chore = make_chore(name='Bins', interval_days=7)

        client.post(reverse('chores:chore_edit', args=[chore.pk]), {
            'name': 'Bins',
            'notes': 'Green bin',
            'recurrence': Recurrence.FIXED,
            'interval_days': 14,
            'next_due': (today + timedelta(days=1)).isoformat(),
        })

        chore.refresh_from_db()
        assert chore.interval_days == 14
        assert chore.recurrence == Recurrence.FIXED
        assert chore.notes == 'Green bin'


class TestConcurrentClaims:
    """Two housemates clicking Done on the same occurrence.

    Rather than racing real threads (flaky, and SQLite serialises writes
    anyway), the competing claim is landed deterministically from inside the
    view's own call to the recurrence engine — the exact window between reading
    next_due and writing it back.
    """

    def test_the_loser_neither_double_advances_nor_double_records(
        self, as_alex, alex, make_chore, monkeypatch, today
    ):
        chore = make_chore(recurrence=Recurrence.INTERVAL, interval_days=7, due_offset=-1)
        occurrence_due = chore.next_due
        sam = Housemate.objects.create(name='Sam')

        real_next_due = chore.next_due + timedelta(days=7)

        def sam_gets_there_first(*args, **kwargs):
            Chore.objects.filter(pk=chore.pk, next_due=occurrence_due).update(
                next_due=real_next_due
            )
            Completion.objects.create(
                chore=chore, housemate=sam,
                due_date=occurrence_due, completed_on=today,
            )
            return real_next_due

        monkeypatch.setattr('chores.views.next_due_date', sam_gets_there_first)

        response = as_alex.post(reverse('chores:done', args=[chore.pk]))

        assert response.status_code == 302
        # One occurrence, one completion — Alex's click did not add a second.
        assert Completion.objects.count() == 1
        assert Completion.objects.get().housemate == sam
        # And the schedule advanced exactly one step, not two.
        chore.refresh_from_db()
        assert chore.next_due == real_next_due

    def test_the_winner_still_succeeds_normally(self, as_alex, alex, make_chore, today):
        chore = make_chore(recurrence=Recurrence.INTERVAL, interval_days=7, due_offset=-1)

        as_alex.post(reverse('chores:done', args=[chore.pk]))

        assert Completion.objects.count() == 1
        assert Completion.objects.get().housemate == alex


class TestMalformedInput:
    """A bad request should be a 4xx, never a 500."""

    @pytest.mark.parametrize('value', ['', 'abc', '999999', '1; DROP TABLE'])
    def test_picking_a_bogus_housemate_is_not_a_server_error(self, client, alex, value):
        response = client.post(reverse('chores:who'), {'housemate': value})

        assert response.status_code == 404
        assert 'housemate_id' not in client.session

    def test_picking_with_the_field_missing_entirely(self, client, alex):
        assert client.post(reverse('chores:who'), {}).status_code == 404

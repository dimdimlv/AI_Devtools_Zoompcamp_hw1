"""Populate a demo household.

Dates are relative to today, so the board always has something in all three
groups no matter when you run it.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from chores.dates import today as today_
from chores.models import Chore, Completion, Housemate, Recurrence

HOUSEMATES = ['Alex', 'Sam', 'Rae']

# (name, notes, recurrence, interval_days, days from today until next due)
CHORES = [
    ('Take the bins out', 'Green bin on the kerb by 7am.', Recurrence.FIXED, 7, -3),
    ('Clean the bathroom', '', Recurrence.FIXED, 14, -1),
    ('Vacuum the hallway', '', Recurrence.INTERVAL, 7, 0),
    ('Water the plants', 'The fern dries out fastest.', Recurrence.INTERVAL, 4, 2),
    ('Wipe the kitchen counters', '', Recurrence.INTERVAL, 3, 3),
    ('Change the bed sheets', '', Recurrence.FIXED, 14, 6),
    ('Descale the kettle', 'Half vinegar, half water.', Recurrence.INTERVAL, 30, 9),
    ('Clean the oven', '', Recurrence.FIXED, 90, 21),
]


class Command(BaseCommand):
    help = 'Create a demo household: housemates, chores and a little history.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing chores, housemates and history first.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        today = today_()

        if options['reset']:
            Completion.objects.all().delete()
            Chore.objects.all().delete()
            Housemate.objects.all().delete()
            self.stdout.write('Cleared existing data.')

        housemates = {}
        for name in HOUSEMATES:
            housemate, _ = Housemate.objects.get_or_create(name=name)
            housemates[name] = housemate

        created = 0
        for name, notes, recurrence, interval, offset in CHORES:
            _, was_created = Chore.objects.get_or_create(
                name=name,
                defaults={
                    'notes': notes,
                    'recurrence': recurrence,
                    'interval_days': interval,
                    'next_due': today + timedelta(days=offset),
                },
            )
            created += was_created

        # A little history, so /history/ is not empty on first look: one on time,
        # one late, one skipped by nobody.
        bins = Chore.objects.get(name='Take the bins out')
        vacuum = Chore.objects.get(name='Vacuum the hallway')
        plants = Chore.objects.get(name='Water the plants')
        if not Completion.objects.exists():
            Completion.objects.create(
                chore=bins, housemate=housemates['Alex'],
                due_date=today - timedelta(days=10), completed_on=today - timedelta(days=10),
            )
            Completion.objects.create(
                chore=vacuum, housemate=housemates['Sam'],
                due_date=today - timedelta(days=9), completed_on=today - timedelta(days=7),
            )
            Completion.objects.create(
                chore=plants, housemate=None,
                due_date=today - timedelta(days=2), completed_on=today - timedelta(days=2),
                was_skipped=True,
            )

        self.stdout.write(self.style.SUCCESS(
            f'{len(housemates)} housemates, {created} new chores '
            f'({Chore.objects.count()} total), {Completion.objects.count()} completions.'
        ))
        self.stdout.write(f"Today is {today}. Run the server and open '/'.")

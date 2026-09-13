from django.core.validators import MinValueValidator
from django.db import models


class Housemate(models.Model):
    """Someone who can claim a chore. Identity is a name, not an account."""

    name = models.CharField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Recurrence(models.TextChoices):
    FIXED = 'FIXED', 'Fixed schedule'
    INTERVAL = 'INTERVAL', 'Interval since last done'


class Chore(models.Model):
    """A recurring task. Carries only its *next* occurrence; history lives in Completion."""

    name = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    recurrence = models.CharField(
        max_length=8,
        choices=Recurrence.choices,
        default=Recurrence.INTERVAL,
    )
    interval_days = models.PositiveIntegerField(
        # The FIXED advance loop steps by interval_days until it passes the completion
        # date, so a zero interval would never terminate.
        validators=[MinValueValidator(1)],
        help_text='Days between occurrences. Must be at least 1.',
    )
    next_due = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['next_due', 'name']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(interval_days__gte=1),
                name='chore_interval_days_at_least_1',
            ),
        ]

    def __str__(self):
        return self.name


class Completion(models.Model):
    """One occurrence of a chore, done or skipped. Append-only history."""

    chore = models.ForeignKey(
        Chore,
        on_delete=models.CASCADE,
        related_name='completions',
    )
    housemate = models.ForeignKey(
        Housemate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completions',
    )
    # Snapshotted so history stays truthful after the chore's schedule moves on.
    due_date = models.DateField()
    completed_on = models.DateField()
    was_skipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_on', '-created_at']

    def __str__(self):
        verb = 'skipped' if self.was_skipped else 'done'
        return f'{self.chore} {verb} on {self.completed_on}'

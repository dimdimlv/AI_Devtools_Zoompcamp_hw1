"""Expose the session identity and the overdue count to every template."""

from .dates import today
from .identity import current_housemate as _current_housemate
from .models import Chore


def household(request):
    return {
        'current_housemate': _current_housemate(request),
        'overdue_count': Chore.objects.filter(
            is_active=True, next_due__lt=today()
        ).count(),
    }

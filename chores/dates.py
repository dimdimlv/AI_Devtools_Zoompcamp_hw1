"""The single source of "what day is it".

Every view calls ``today()`` rather than ``date.today()`` or ``localdate()``
directly, for two reasons: the answer must come from the household's TIME_ZONE,
and tests need one place to freeze.
"""

from django.utils.timezone import localdate


def today():
    return localdate()

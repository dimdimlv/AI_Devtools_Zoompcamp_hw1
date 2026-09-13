"""Session identity: a name, not an account.

The whole auth story is "which housemate are you", kept in the session under
one key. Nothing here grants permission — anyone who can reach the page is
trusted; the identity only decides whose name lands on a completion.
"""

from .models import Housemate

SESSION_KEY = 'housemate_id'


def current_housemate(request):
    """The Housemate for this session, or None.

    A session pointing at a housemate who has since been deleted or
    deactivated degrades to None rather than raising.
    """
    housemate_id = request.session.get(SESSION_KEY)
    if not housemate_id:
        return None
    return Housemate.objects.filter(pk=housemate_id, is_active=True).first()


def set_current_housemate(request, housemate):
    request.session[SESSION_KEY] = housemate.pk


def clear_current_housemate(request):
    request.session.pop(SESSION_KEY, None)

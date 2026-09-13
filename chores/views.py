from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .dates import today as today_
from .forms import ChoreForm
from .identity import current_housemate, set_current_housemate
from .models import Chore, Completion, Housemate
from .recurrence import next_due_date

UPCOMING_WINDOW_DAYS = 14


def board(request):
    """What needs doing right now, in three groups."""
    today = today_()
    horizon = today + timedelta(days=UPCOMING_WINDOW_DAYS)

    due = list(Chore.objects.filter(is_active=True, next_due__lte=today))
    # Most late first — the point of the board is the worst offender at the top.
    # Chore.Meta already orders by next_due ascending, which is exactly that.
    overdue = [c for c in due if c.next_due < today]
    due_today = [c for c in due if c.next_due == today]

    upcoming = list(
        Chore.objects.filter(
            is_active=True, next_due__gt=today, next_due__lte=horizon
        )
    )

    # Templates stay dumb: lateness is measured against the view's `today`, not
    # a second, possibly different, call to the clock.
    for chore in overdue:
        chore.late_days = chore.days_late(today)

    return render(request, 'board.html', {
        'today': today,
        'overdue': overdue,
        'due_today': due_today,
        'upcoming': upcoming,
        'upcoming_window_days': UPCOMING_WINDOW_DAYS,
    })


def who(request):
    """Pick your name. No password, no account."""
    if request.method == 'POST':
        # A missing or non-numeric value is a malformed request, not a server
        # error — pk= straight from POST would raise ValueError and 500.
        raw = request.POST.get('housemate', '')
        housemate = (
            Housemate.objects.filter(pk=raw, is_active=True).first()
            if raw.isdigit()
            else None
        )
        if housemate is None:
            raise Http404('No such housemate.')
        set_current_housemate(request, housemate)
        messages.success(request, f'You are {housemate.name}.')
        return redirect(_safe_next(request) or 'chores:board')

    return render(request, 'who.html', {
        'housemates': Housemate.objects.filter(is_active=True),
        'next': request.GET.get('next', ''),
    })


def _safe_next(request):
    """Only ever redirect back to a path on this site."""
    target = request.POST.get('next', '')
    if target.startswith('/') and not target.startswith('//'):
        return target
    return None


@require_POST
def done(request, pk):
    return _record(request, pk, was_skipped=False)


@require_POST
def skip(request, pk):
    return _record(request, pk, was_skipped=True)


def _record(request, pk, was_skipped):
    """Write a Completion and advance the chore's schedule.

    Skipping takes the same path as claiming — it advances the schedule
    identically — but credits nobody.
    """
    housemate = current_housemate(request)
    if housemate is None and not was_skipped:
        # Claiming needs a name on it; nothing is mutated on the way out.
        return redirect(f"{reverse('chores:who')}?next={reverse('chores:board')}")

    today = today_()

    with transaction.atomic():
        # select_for_update locks the row on backends that support it. SQLite
        # is not one of them (has_select_for_update is False, so Django simply
        # omits the clause), which is why the advance below is a compare-and-
        # swap rather than a plain save: it is the part that actually holds.
        chore = get_object_or_404(
            Chore.objects.select_for_update(), pk=pk, is_active=True
        )
        occurrence_due = chore.next_due
        new_due = next_due_date(
            chore.recurrence, occurrence_due, today, chore.interval_days
        )

        # Advance only if nobody has moved the chore on since we read it. Two
        # housemates clicking Done at the same moment both reach here with the
        # same occurrence_due; exactly one update matches a row.
        advanced = Chore.objects.filter(
            pk=chore.pk, next_due=occurrence_due
        ).update(next_due=new_due)

        if not advanced:
            messages.info(
                request, f'{chore.name} was already taken care of by someone else.'
            )
            return redirect('chores:board')

        Completion.objects.create(
            chore=chore,
            housemate=None if was_skipped else housemate,
            due_date=occurrence_due,
            completed_on=today,
            was_skipped=was_skipped,
        )

    verb = 'Skipped' if was_skipped else 'Done'
    messages.success(
        request, f'{verb}: {chore.name}. Next due {new_due:%a %-d %b}.'
    )
    return redirect('chores:board')


def history(request):
    """Everything that has been done or skipped, newest first."""
    completions = Completion.objects.select_related('chore', 'housemate')
    paginator = Paginator(completions, 25)
    page = paginator.get_page(request.GET.get('page'))

    for completion in page:
        completion.days_late = (completion.completed_on - completion.due_date).days

    return render(request, 'history.html', {'page': page})


def chore_list(request):
    return render(request, 'chore_list.html', {
        'chores': Chore.objects.filter(is_active=True),
        'today': today_(),
    })


def chore_new(request):
    form = ChoreForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        chore = form.save()
        messages.success(request, f'Added {chore.name}.')
        return redirect('chores:board')
    return render(request, 'chore_form.html', {'form': form, 'chore': None})


def chore_edit(request, pk):
    chore = get_object_or_404(Chore, pk=pk, is_active=True)
    form = ChoreForm(request.POST or None, instance=chore)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Updated {chore.name}.')
        return redirect('chores:chore_list')
    return render(request, 'chore_form.html', {'form': form, 'chore': chore})


def chore_delete(request, pk):
    """Soft delete — the chore leaves the board, its history stays."""
    chore = get_object_or_404(Chore, pk=pk, is_active=True)
    if request.method == 'POST':
        chore.is_active = False
        chore.save(update_fields=['is_active'])
        messages.success(request, f'Removed {chore.name}. Its history is kept.')
        return redirect('chores:chore_list')
    return render(request, 'chore_confirm_delete.html', {'chore': chore})

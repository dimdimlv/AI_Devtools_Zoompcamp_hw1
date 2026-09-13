from django import forms

from .models import Chore


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['name', 'notes', 'recurrence', 'interval_days', 'next_due']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'next_due': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
        labels = {'next_due': 'Next due', 'interval_days': 'Every (days)'}
        help_texts = {
            'recurrence': 'Fixed keeps the calendar slot; interval counts from '
                          'the day it was last done.',
        }

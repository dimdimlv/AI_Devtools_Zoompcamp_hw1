from django.contrib import admin

from .models import Chore, Completion, Housemate


@admin.register(Housemate)
class HousemateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'recurrence', 'interval_days', 'next_due', 'is_active']
    list_filter = ['recurrence', 'is_active']
    search_fields = ['name', 'notes']
    ordering = ['next_due', 'name']


@admin.register(Completion)
class CompletionAdmin(admin.ModelAdmin):
    list_display = ['chore', 'housemate', 'due_date', 'completed_on', 'was_skipped']
    list_filter = ['was_skipped', 'completed_on']
    search_fields = ['chore__name', 'housemate__name']
    list_select_related = ['chore', 'housemate']
    date_hierarchy = 'completed_on'

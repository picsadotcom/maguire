from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "id", "source_model", "source_id", "event_at", "event_type",
        "created_at", "updated_at",
        "node_id"
    ]
    list_filter = [
        "source_model", "event_at", "event_type",
        "created_at", "updated_at"
    ]
    search_fields = [
        "source_id", "event_at"
    ]
    ordering = [
        "-created_at"
    ]

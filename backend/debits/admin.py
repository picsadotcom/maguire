from django.contrib import admin
from import_export.admin import ExportMixin

from debits.models import Debit


@admin.register(Debit)
class DebitAdmin(ExportMixin, admin.ModelAdmin):
    list_display = [
        "id", "client", "status", "downstream_reference", "reference", "load_attempts",
        "scheduled_at", "loaded_at", "created_at", "updated_at",
        "provider_reference", "account_name", "account_number", "branch_code", "account_type",
        "amount", "callback_url", "node_id",
    ]
    list_filter = [
        "status", "load_attempts", "branch_code", "account_type", "provider",
        "scheduled_at", "loaded_at", "created_at", "updated_at",
    ]
    search_fields = [
        "client", "downstream_reference", "reference", "provider_reference",
        "account_name", "account_number", "branch_code"
    ]
    ordering = [
        "-created_at"
    ]

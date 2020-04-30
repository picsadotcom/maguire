import reversion

from django.utils.encoding import python_2_unicode_compatible
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from maguire.models import AppModel

from events.models import Event


@reversion.register()
@python_2_unicode_compatible
class Debit(AppModel):
    """
    Debit Model
    """
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("loaded", "Loaded"),
        ("successful", "Successful"),
        ("failed", "Failed"),
    )
    ACCOUNT_TYPE_CHOICES = (
        ("savings", "Savings"),
        ("current", "Current"),
    )
    # Optional Identifing information
    client = models.CharField(
        max_length=50,
        verbose_name=_("Client"),
        help_text=_("Client identifier (UUID, number, reference, etc.) from your system"),
        null=True, blank=True
    )
    downstream_reference = models.CharField(
        max_length=50,
        verbose_name=_("Reference"),
        unique=True,
        help_text=_("Payment reference (UUID, number, reference, etc.) from your system. "
                    "This must either be None or should be unique to prevent duplication"),
        null=True, blank=True
    )
    callback_url = models.CharField(
        max_length=500,
        verbose_name=_("Callback URL"),
        help_text=_("URL to callback when debit moves to successful or failed"),
        null=True, blank=True
    )
    # Banking details
    account_name = models.CharField(
        max_length=60,
        verbose_name=_("Account Name"),
        help_text=_("Bank account holder's name, unvalidated")
    )
    account_number = models.CharField(
        max_length=15,
        help_text=_("Bank account Number"))
    branch_code = models.CharField(max_length=6)
    account_type = models.CharField(
        choices=ACCOUNT_TYPE_CHOICES, max_length=30,
        null=True, blank=True)
    # Debit details
    status = models.CharField(
        choices=STATUS_CHOICES, max_length=30,
        default="pending")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2)
    reference = models.CharField(
        null=True, blank=True,
        max_length=9,
        verbose_name=_("Debit Reference"),
        help_text=_("Unique 9 digit validated debit reference, provider agnostic"))
    provider = models.CharField(
        max_length=50,
        verbose_name=_("Provider"),
        help_text=_("Upstream Debit provider, set by provider module"),
        null=True, blank=True
    )
    provider_reference = models.CharField(
        max_length=200,
        verbose_name=_("Provider Reference"),
        help_text=_("Upstream Debit provider reference for lookups"),
        null=True, blank=True
    )
    provider_status = models.CharField(
        max_length=200,
        verbose_name=_("Provider Status"),
        help_text=_("Upstream Debit provider status for error/success checks"),
        null=True, blank=True
    )
    scheduled_at = models.DateTimeField(
        verbose_name=_("Scheduled at"),
        help_text=_("Date and time after which pending debits will be loaded"),
        null=True, blank=True)
    loaded_at = models.DateTimeField(
        verbose_name=_("Loaded at"),
        help_text=_("Date and time that debit was loaded to provider"),
        null=True, blank=True)
    load_attempts = models.IntegerField(
        default=0,
        verbose_name=_("Load Attempts"),
        help_text=_("Number of times maguire has attmepted to load the debit"))
    last_error = models.TextField(
        verbose_name=_("Last Error"),
        help_text=_("The error message received on the last attempt to load the debit"),
        null=True, blank=True)
    created_by = models.ForeignKey(
        User, related_name='debits_created', null=True, blank=True,
        on_delete=models.CASCADE)
    updated_by = models.ForeignKey(
        User, related_name='debits_updated', null=True, blank=True,
        on_delete=models.CASCADE)

    @property
    def node_id(self):
        from maguire.utils import b64_from_uuid
        return b64_from_uuid(self.id, "DebitNode").decode("utf-8")

    def as_json(self):
        """
        Prepares this Debit for JSON serialization
        """
        return {
            'id': str(self.id),
            'client': self.client,
            'downstream_reference': self.downstream_reference,
            'callback_url': self.callback_url,
            'account_name': self.account_name,
            'account_number': self.account_number,
            'branch_code': self.branch_code,
            'account_type': self.account_type,
            'status': self.status,
            'amount': str(self.amount),
            'reference': self.reference,
            'provider': self.provider,
            'provider_reference': self.provider_reference,
            'provider_status': self.provider_status,
            'scheduled_at': self.scheduled_at.isoformat() if self.loaded_at else None,
            'loaded_at': self.loaded_at.isoformat() if self.loaded_at else None,
            'load_attempts': self.load_attempts,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by.id if self.created_by else None,
            'updated_at': self.updated_at.isoformat(),
            'updated_by': self.updated_by.id if self.updated_by else None,
        }

    def save(self, *args, **kwargs):
        if self.reference is None:
            self.reference = generate_unique_debit_reference(length=9)
        super(Debit, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.id)


@receiver(post_save, sender=Debit)
def create_event_debit(sender, instance, created, **kwargs):
    """ Post save hook that creates a model.created Event
    """
    if created:
        source_model = ContentType.objects.get(app_label='debits', model='debit')
        Event.objects.create(**{
            "source_model": source_model,
            "source_id": instance.id,
            "event_at": timezone.now(),
            "event_type": "model.created",
            "event_data": instance.as_json(),
            "created_by": instance.created_by
        })


def generate_unique_debit_reference(length=9, attempts=0):
    from maguire.utils import random_digits, calculate_luhn

    source = random_digits(length-1)
    checksum = calculate_luhn(source)
    unique_reference = str(source) + str(checksum)

    try:
        Debit.objects.get(reference=unique_reference)
        if attempts < 10:
            generate_unique_debit_reference(length=length, attempts=attempts+1)
        else:
            return "Aborting unique_reference generation after 10 failed attempts"
    except Debit.DoesNotExist:
        return unique_reference

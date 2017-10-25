from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import now
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.contrib.postgres.fields import JSONField
from django.db.models.signals import post_save
from django.dispatch import receiver

from maguire.models import AppModel


@python_2_unicode_compatible
class Event(AppModel):

    """
    Event Model
    """

    source_model = models.ForeignKey(
        ContentType, null=True, blank=True,
        on_delete=models.CASCADE)
    source_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('source_model', 'source_id')
    event_at = models.DateTimeField(
        default=now,
        help_text=_("Time event ocurred, defaults to now"))
    event_type = models.CharField(
        verbose_name=_("Event Type"), max_length=60,
        help_text=_("e.g. client_terminated / client_suspended / "
                    "savings_adjustment"))
    event_data = JSONField(
        verbose_name=_("Event Data"),
        blank=True, default=dict,
        help_text=_(
            "Data about the Event with keys and values, e.g. description: "
            "Client Terminated"))

    created_by = models.ForeignKey(
        User, related_name='events_created', null=True, blank=True,
        on_delete=models.CASCADE)
    updated_by = models.ForeignKey(
        User, related_name='events_updated', null=True, blank=True,
        on_delete=models.CASCADE)
    user = property(lambda self: self.created_by)

    @property
    def node_id(self):
        from maguire.utils import b64_from_uuid
        return b64_from_uuid(self.id, "EventNode").decode("utf-8")

    def as_json(self):
        """
        Prepares this Event for JSON serialization
        """
        return {
            'id': str(self.id),
            'source_model': self.source_model.id if self.source_model else None,  # noqa
            'source_id': str(self.source_id) if self.source_id else None,
            'event_at': self.event_at.isoformat(),
            'event_type': self.event_type,
            'event_data': self.event_data,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by.id if self.created_by else None,
            'updated_at': self.updated_at.isoformat(),
            'updated_by': self.updated_by.id if self.updated_by else None,
        }

    def __str__(self):
        return str(self.id)


@receiver(post_save, sender=Event)
def event_post_save(sender, instance, created, **kwargs):
    """ Post save hook that fires tasks based on the created event type
    """
    from events import tasks
    if created:
        def run_task_event_type():
            try:
                getattr(tasks, instance.event_type.replace(".", "_")
                        ).apply_async(kwargs={"event_id": instance.id})
            except:
                pass
        transaction.on_commit(run_task_event_type)

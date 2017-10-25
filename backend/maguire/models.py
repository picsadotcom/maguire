import uuid

from django.db import models


class AppQuerySet(models.QuerySet):
    pass


class AppManager(models.Manager):
    queryset_class = AppQuerySet


class AppModelMeta(type(models.Model)):
    pass


class AppModel(models.Model):
    __metaclass__ = AppModelMeta

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = AppManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super(AppModel, self).save(*args, **kwargs)

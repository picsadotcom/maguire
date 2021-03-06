# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-24 14:16
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_id', models.UUIDField(blank=True, null=True)),
                ('event_at', models.DateTimeField(default=django.utils.timezone.now, help_text='Time event ocurred, defaults to now')),
                ('event_type', models.CharField(help_text='e.g. client_terminated / client_suspended / savings_adjustment', max_length=60, verbose_name='Event Type')),
                ('event_data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='Data about the Event with keys and values, e.g. description: Client Terminated', verbose_name='Event Data')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='events_created', to=settings.AUTH_USER_MODEL)),
                ('source_model', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='events_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

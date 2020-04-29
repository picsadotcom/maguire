# Generated by Django 2.1.15 on 2020-04-29 12:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('debits', '0004_auto_20190409_0715'),
    ]

    operations = [
        migrations.AlterField(
            model_name='debit',
            name='downstream_reference',
            field=models.CharField(blank=True, help_text='Payment reference (UUID, number, reference, etc.) from your systemThis must either be None or should be unique to prevent duplication', max_length=50, null=True, unique=True, verbose_name='Reference'),
        ),
    ]
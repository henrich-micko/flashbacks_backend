# Generated by Django 5.0.7 on 2025-02-04 15:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0021_eventpostertemplate_alter_eventinvite_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventqrcode',
            name='event',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='event.event'),
        ),
    ]

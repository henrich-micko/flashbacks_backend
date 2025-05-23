# Generated by Django 5.0.7 on 2025-02-04 10:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0020_eventinvite'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventPosterTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=10, unique=True)),
                ('html_file', models.CharField(max_length=15)),
            ],
        ),
        migrations.AlterField(
            model_name='eventinvite',
            name='status',
            field=models.IntegerField(choices=[(0, 'pending'), (1, 'accept'), (2, 'decline')], default=0),
        ),
        migrations.CreateModel(
            name='EventQrCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, upload_to='event_qrcode/')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='event.event', unique=True)),
            ],
        ),
    ]

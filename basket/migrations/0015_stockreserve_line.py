# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-12-21 14:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0014_stockreserve_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockreserve',
            name='line',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='stock_reserve_lines', to='basket.Line'),
        ),
    ]

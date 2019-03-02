# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-12-21 08:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0012_auto_20171221_1034'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockreserve',
            name='basket',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='stock_reserve', to='basket.Basket'),
        ),
    ]
# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-09-18 11:40
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0075_auto_20170915_1211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contractorcatalogue',
            name='city',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='logistics_exchange.City'),
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-02-04 18:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0011_auto_20170204_0311'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='from_call_center',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='from_sklad',
            field=models.TextField(blank=True, null=True),
        ),
    ]

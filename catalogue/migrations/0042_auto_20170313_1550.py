# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-03-13 12:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0041_auto_20170119_2254'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='item_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-07-24 11:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0057_auto_20170710_1659'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productattribute',
            name='id_attribute',
            field=models.IntegerField(blank=True),
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-12-04 20:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0016_auto_20161129_0847'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='artikul',
            field=models.CharField(default='', max_length=128),
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-01-23 09:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0002_auto_20161208_1433'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockrecord',
            name='is_our_storage',
            field=models.BooleanField(default=False, verbose_name='Остатки с нашего склада?'),
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-09-20 15:04
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0077_merge_20170920_1028'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='cancel_reason',
        ),
        migrations.RemoveField(
            model_name='product',
            name='driver_status',
        ),
        migrations.RemoveField(
            model_name='product',
            name='move_reason',
        ),
    ]

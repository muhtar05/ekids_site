# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-11-01 10:21
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0044_order_order_move_reason'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='from_call_center',
            new_name='order_comment',
        ),
        migrations.RemoveField(
            model_name='order',
            name='from_sklad',
        ),
    ]
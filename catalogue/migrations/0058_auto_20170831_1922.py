# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-08-31 16:22
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0057_remove_product_procure_datetime'),
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
    ]
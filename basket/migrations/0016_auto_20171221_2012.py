# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-12-21 17:12
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0015_stockreserve_line'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stockreserve',
            name='basket',
        ),
        migrations.RemoveField(
            model_name='stockreserve',
            name='product',
        ),
        migrations.RemoveField(
            model_name='stockreserve',
            name='quantity',
        ),
    ]
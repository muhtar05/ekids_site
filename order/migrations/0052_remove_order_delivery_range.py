# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-12-14 09:08
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0051_auto_20171217_0733'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='delivery_range',
        ),
    ]

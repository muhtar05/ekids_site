# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-08-24 15:30
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0056_product_procure_datetime'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='procure_datetime',
        ),
    ]

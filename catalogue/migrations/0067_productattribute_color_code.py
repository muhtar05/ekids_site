# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-08-07 13:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0066_product_num_allocated'),
    ]

    operations = [
        migrations.AddField(
            model_name='productattribute',
            name='color_code',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
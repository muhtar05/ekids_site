# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-07-18 07:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0058_product_is_show'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='num_in_stock',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Number in stock'),
        ),
    ]

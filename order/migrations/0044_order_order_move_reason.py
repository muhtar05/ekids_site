# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-10-19 06:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0043_remove_order_order_move_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_move_reason',
            field=models.TextField(blank=True, verbose_name='Причина переноса заказа'),
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-09-08 09:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0031_merge_20170904_1725'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_cancel_reason',
            field=models.TextField(blank=True, verbose_name='Причина отмены заказа'),
        ),
    ]
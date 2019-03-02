# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-09-01 13:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0058_auto_20170831_1922'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='cancel_reason',
            field=models.TextField(blank=True, verbose_name='Причина отмены'),
        ),
        migrations.AddField(
            model_name='product',
            name='driver_status',
            field=models.SmallIntegerField(choices=[(0, 'Нет'), (1, 'Забрал'), (2, 'Отменен'), (3, 'Перенесен')], default=0, verbose_name='Статус водителя'),
        ),
    ]

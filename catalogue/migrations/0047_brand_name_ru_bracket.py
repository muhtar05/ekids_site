# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-05-24 09:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0046_auto_20170519_1304'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='name_ru_bracket',
            field=models.CharField(blank=True, max_length=255, verbose_name='Для русских брендов'),
        ),
    ]
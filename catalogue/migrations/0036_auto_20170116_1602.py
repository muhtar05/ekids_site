# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-01-16 16:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0035_merge_20170109_0922'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='display_order',
            field=models.PositiveIntegerField(default=100, help_text='Бренд со значением поле 0 будет первым и т.д. (по умолчанию 100)', verbose_name='Последовательность вывода'),
        ),
        migrations.AddField(
            model_name='brand',
            name='slug',
            field=models.SlugField(editable=False, max_length=255, null=True, unique=True, verbose_name='Slug'),
        ),
    ]

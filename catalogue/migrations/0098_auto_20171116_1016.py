# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-11-16 07:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0097_merge_20171114_1957'),
    ]

    operations = [
        migrations.AddField(
            model_name='productrecommendation',
            name='weight',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Weight'),
        ),
        migrations.AlterField(
            model_name='productrecommendation',
            name='ranking',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Ranking'),
        ),
    ]

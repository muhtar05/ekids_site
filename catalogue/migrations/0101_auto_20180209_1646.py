# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-02-09 13:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0100_productimage_is_check'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='model_id',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='Id модели (Яндекс.Маркет)'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_corrected',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Отткорректированная цена(для статистики)'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_min_market',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Минимальная цена на маркете'),
        ),
    ]

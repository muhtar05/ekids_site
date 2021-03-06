# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-29 08:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0015_product_tax'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='age',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Возраст'),
        ),
        migrations.AlterField(
            model_name='product',
            name='brand',
            field=models.CharField(blank=True, max_length=150, null=True, verbose_name='Бренд'),
        ),
        migrations.AlterField(
            model_name='product',
            name='country_manufacter',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Страна'),
        ),
        migrations.AlterField(
            model_name='product',
            name='season',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Сезон'),
        ),
        migrations.AlterField(
            model_name='product',
            name='sex',
            field=models.SmallIntegerField(choices=[(0, 'Унисекс'), (1, 'Мужской'), (2, 'Женский')], default=0, verbose_name='Пол'),
        ),
    ]

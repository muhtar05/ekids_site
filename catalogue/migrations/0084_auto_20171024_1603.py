# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-10-24 13:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0083_merge_20171016_1042'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='full_path_category_google',
            field=models.CharField(blank=True, help_text='Пример: Предметы одежды и принадлежности > Одежда > Верхняя одежда > Дождевая одежда', max_length=255, null=True, verbose_name='Категории товара в соответствии с классификацией Google'),
        ),
        migrations.AlterField(
            model_name='product',
            name='old_slug',
            field=models.CharField(blank=True, max_length=250, null=True, verbose_name='Старый slug товара (для редиректа со старого url на новый)'),
        ),
    ]
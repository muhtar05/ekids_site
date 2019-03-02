# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-01-17 10:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0036_auto_20170116_1602'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Описание бренда'),
        ),
        migrations.AlterField(
            model_name='brand',
            name='slug',
            field=models.SlugField(max_length=255, null=True, unique=True, verbose_name='Slug'),
        ),
    ]
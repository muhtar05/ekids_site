# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-10-11 10:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0079_merge_20170925_1157'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='old_slug',
            field=models.CharField(blank=True, max_length=250, null=True, verbose_name='Старый slug товара(для редиректа со старого url на новый)'),
        ),
    ]

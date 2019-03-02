# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-06-20 10:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0050_category_is_accessory'),
    ]

    operations = [
        migrations.AddField(
            model_name='attributeoptiongroup',
            name='code',
            field=models.SlugField(default='', max_length=128, verbose_name='Code'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='attributeoptiongroup',
            name='name',
            field=models.CharField(blank=True, max_length=128, null=True, verbose_name='Name'),
        ),
    ]

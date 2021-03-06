# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-09-13 06:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0073_auto_20170908_1436'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='id_option',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_p',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В предложном падеже'),
        ),
        migrations.AlterField(
            model_name='productattributeoption',
            name='case_r',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='В родительном падеже'),
        ),
    ]

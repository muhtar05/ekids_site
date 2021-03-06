# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-06-20 11:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0051_auto_20170620_1341'),
    ]

    operations = [
        migrations.AddField(
            model_name='attributeoption',
            name='id_attribute_option',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productattribute',
            name='id_attribute',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='productattribute',
            name='option_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='catalogue.AttributeOptionGroup', verbose_name='Option Group'),
        ),
    ]

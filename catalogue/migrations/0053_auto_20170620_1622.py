# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-06-20 13:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0052_auto_20170620_1444'),
    ]

    operations = [
        migrations.AddField(
            model_name='productattribute',
            name='display_order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productattribute',
            name='legend',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='productattribute',
            name='type_group',
            field=models.CharField(choices=[('maincharact', 'Главные характеристики'), ('transcharact', 'Транспортные характеристики')], default='maincharact', max_length=50),
        ),
        migrations.AddField(
            model_name='productattribute',
            name='widget_type_display',
            field=models.CharField(choices=[('checkbox_list', 'Чекбоксы'), ('select_list', 'Селектор'), ('slider_input', 'Ползунок')], default='checkbox_list', max_length=50),
        ),
    ]
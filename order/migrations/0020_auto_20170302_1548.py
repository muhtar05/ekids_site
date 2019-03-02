# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-03-02 12:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0019_auto_20170301_1828'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='statusgroup',
            options={'verbose_name': 'Пользовательский статус', 'verbose_name_plural': 'Пользовательские статусы'},
        ),
        migrations.AddField(
            model_name='statusgroup',
            name='status_class',
            field=models.CharField(blank=True, max_length=70, null=True),
        ),
    ]

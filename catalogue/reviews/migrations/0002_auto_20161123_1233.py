# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-23 12:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productreview',
            name='score',
        ),
        migrations.AddField(
            model_name='productreview',
            name='age_child',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='productreview',
            name='dignity',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='productreview',
            name='impression',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='productreview',
            name='limitations',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='productreview',
            name='service_ability_score',
            field=models.SmallIntegerField(choices=[(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='productreview',
            name='workmanship_score',
            field=models.SmallIntegerField(choices=[(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], default=0),
            preserve_default=False,
        ),
    ]
# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-11-14 11:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0095_merge_20171110_1826'),
    ]

    operations = [
        migrations.AddField(
            model_name='contractorcatalogue',
            name='cm_code',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
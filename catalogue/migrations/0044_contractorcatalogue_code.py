# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-04-21 18:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0043_auto_20170331_1523'),
    ]

    operations = [
        migrations.AddField(
            model_name='contractorcatalogue',
            name='code',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]

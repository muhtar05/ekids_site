# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-12-28 15:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0031_merge_20161223_0749'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='video_container',
            field=models.CharField(max_length=255, null=True),
        ),
    ]